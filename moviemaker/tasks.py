import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, NewType

import youtube_dl
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files import File
from django.db import transaction
from moviepy.editor import VideoFileClip, concatenate_videoclips
from youtube_dl.utils import DownloadError

from moviemaker.models import VideoFile
from moviemaker.utils import hashed

logger = get_task_logger(__name__)


VideoId = NewType('VideoId', str)


@shared_task(ack_late=True, ignore_result=True)
def cleanup_old_videos() -> None:
    files_to_remove: List[Path] = []

    def delete_files() -> None:
        for file in files_to_remove:
            file.unlink()

    with transaction.atomic():
        transaction.on_commit(delete_files)
        videos = (
            VideoFile.objects
            .filter(last_used_at__lt=datetime.utcnow() - timedelta(days=3))
            .order_by('last_used_at')
        )
        for video in videos:
            video.delete()
            files_to_remove.append(Path(video.file.path))

    logger.info(f"Deleted {len(files_to_remove)} old videos")


@shared_task(
    ack_late=True,
    autoretry_for=(DownloadError,),
    retry_backoff=5,
    default_retry_delay=3.0,
    max_retries=5,
    rate_limit=settings.YOUTUBE_RATE_LIMIT,
)
def download_youtube_video(youtube_video_id: str) -> VideoId:
    target_video_id = hashed(youtube_video_id)[:32]
    try:
        target_video: VideoFile = VideoFile.objects.get(id=target_video_id)
    except VideoFile.DoesNotExist:
        pass
    else:
        target_video.save(update_fields=('last_used_at',))
        logger.debug(f"Download video {youtube_video_id}: found in cache")
        return VideoId(target_video.id)

    logger.info(f"Download video {youtube_video_id}: started")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        with youtube_dl.YoutubeDL(dict(
                format=settings.YOUTUBE_VIDEO_FORMAT,
                outtmpl=str(tmp_dir_path / f"{target_video_id}.%(ext)s"),
                ratelimit=None,
                quiet=True,
                noprogress=True,
                logger=logger,
        )) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={youtube_video_id}"])
        logger.debug(f"Download video {youtube_video_id}: saving")
        video_file_path = list(tmp_dir_path.glob(f"{target_video_id}.*"))[0]
        with VideoFileClip(filename=str(video_file_path)) as clip:
            video_duration = clip.duration
            video_width, video_height = clip.size
        with video_file_path.open(mode='rb') as file:
            target_video = VideoFile(
                id=target_video_id,
                duration=video_duration,
                width=video_width,
                height=video_height,
                file=File(file, name=video_file_path.parts[-1]),
            )
            target_video.save()
    logger.info(f"Download video {youtube_video_id}: finished")
    return VideoId(target_video.id)


@shared_task(ack_late=True)
def transform_video(
        src_video_id: VideoId,
        cut_from_ms: Optional[int] = None,
        cut_to_ms: Optional[int] = None,
) -> VideoId:
    src_video: VideoFile = VideoFile.objects.get(id=src_video_id)
    src_video.save(update_fields=('last_used_at',))

    target_video_id = hashed(f"{src_video_id}/{cut_from_ms}/{cut_to_ms}")[:32]
    try:
        target_video: VideoFile = VideoFile.objects.get(id=target_video_id)
    except VideoFile.DoesNotExist:
        pass
    else:
        target_video.save(update_fields=('last_used_at',))
        logger.debug(f"Transform video {src_video.id}: found in cache")
        return VideoId(target_video.id)

    if cut_from_ms is None and cut_to_ms is None:
        return src_video_id

    if cut_from_ms is None:
        cut_from_ms = 0

    logger.info(f"Transform video {src_video.id}: started")
    with VideoFileClip(filename=src_video.file.path) as clip:
        if cut_to_ms:
            clip = clip.subclip(cut_from_ms / 1000, cut_to_ms / 1000)
        else:
            clip = clip.subclip(cut_from_ms / 1000)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            video_file_path = tmp_dir_path / f"{target_video_id}.{settings.VIDEO_TEMP_OUTPUT_FORMAT}"
            clip.write_videofile(
                filename=str(video_file_path),
                logger=None,
                **settings.VIDEO_TEMP_ENCODER_SETTINGS,
            )
            logger.debug(f"Transform video {src_video.id}: saving")
            with video_file_path.open(mode='rb') as file:
                target_video = VideoFile(
                    id=target_video_id,
                    duration=clip.duration,
                    width=clip.size[0],
                    height=clip.size[1],
                    file=File(file, name=video_file_path.parts[-1]),
                )
                target_video.save()
    logger.info(f"Transform video {src_video.id}: finished")
    return VideoId(target_video.id)


@shared_task(ack_late=True)
def concatenate_videos(src_video_ids: List[VideoId]) -> VideoId:
    src_videos: List[VideoFile] = []
    for src_video_id in src_video_ids:
        src_video: VideoFile = VideoFile.objects.get(id=src_video_id)
        src_video.save(update_fields=('last_used_at',))
        src_videos.append(src_video)

    if len(src_videos) == 1:
        return src_video_ids[0]

    src_videos_verb = '[' + ', '.join(src_video_ids) + ']'

    target_video_id = hashed('/'.join(src_video_ids))[:32]
    try:
        target_video: VideoFile = VideoFile.objects.get(id=target_video_id)
    except VideoFile.DoesNotExist:
        pass
    else:
        target_video.save(update_fields=('last_used_at',))
        logger.debug(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): found in cache")
        return VideoId(target_video.id)

    logger.info(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): started")
    clips = [VideoFileClip(filename=video.file.path) for video in src_videos]
    try:
        with concatenate_videoclips(clips) as clip:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_dir_path = Path(tmp_dir)
                video_file_path = tmp_dir_path / f"{target_video_id}.{settings.VIDEO_FINAL_OUTPUT_FORMAT}"
                clip.write_videofile(
                    filename=str(video_file_path),
                    logger=None,
                    **settings.VIDEO_FINAL_ENCODER_SETTINGS,
                )
                logger.debug(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): saving")
                with video_file_path.open(mode='rb') as file:
                    target_video = VideoFile(
                        id=target_video_id,
                        duration=clip.duration,
                        width=clip.size[0],
                        height=clip.size[1],
                        file=File(file, name=video_file_path.parts[-1]),
                    )
                    target_video.save()
    finally:
        logger.debug(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): cleanup")
        for clip in clips:
            clip.close()
    logger.info(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): finished")
    return VideoId(target_video.id)
