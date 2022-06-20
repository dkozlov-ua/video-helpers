import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import youtube_dl
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files import File
from django.db import transaction
from moviepy.editor import VideoFileClip, concatenate_videoclips
from youtube_dl.utils import DownloadError

from moviemaker.models import VideoFile

logger = get_task_logger(__name__)


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
def download_youtube_video(video_id: str) -> VideoFile:
    try:
        video = VideoFile.objects.get(id=video_id)
    except VideoFile.DoesNotExist:
        pass
    else:
        video.save(update_fields=('last_used_at',))
        logger.debug(f"Download video {video_id}: found in cache")
        return video

    logger.info(f"Download video {video_id}: started")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        with youtube_dl.YoutubeDL(dict(
                format=settings.YOUTUBE_VIDEO_FORMAT,
                outtmpl=str(tmp_dir_path / f"{video_id}.%(ext)s"),
                ratelimit=None,
                quiet=True,
                noprogress=True,
                logger=logger,
        )) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        logger.debug(f"Download video {video_id}: saving")
        video_file_path = list(tmp_dir_path.glob(f"{video_id}.*"))[0]
        with VideoFileClip(filename=str(video_file_path)) as clip:
            video_duration = clip.duration
            video_width, video_height = clip.size
        with video_file_path.open(mode='rb') as file:
            video = VideoFile(
                id=video_id,
                duration=video_duration,
                width=video_width,
                height=video_height,
                file=File(file, name=video_file_path.parts[-1]),
            )
            video.save()
    logger.info(f"Download video {video_id}: finished")
    return video


@shared_task(ack_late=True)
def transform_video(src_video: VideoFile, cut_from_ms: Optional[int] = None, cut_to_ms: Optional[int] = None) \
        -> VideoFile:
    src_video.save(update_fields=('last_used_at',))

    if cut_from_ms is None and cut_to_ms is None:
        return src_video

    if cut_from_ms is None:
        cut_from_ms = 0

    video_id = str(uuid.uuid4())

    logger.info(f"Transform video {src_video.id}: started")
    with VideoFileClip(filename=src_video.file.path) as clip:
        if cut_to_ms:
            clip = clip.subclip(cut_from_ms / 1000, cut_to_ms / 1000)
        else:
            clip = clip.subclip(cut_from_ms / 1000)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            video_file_path = tmp_dir_path / f"{video_id}.{settings.VIDEO_OUTPUT_FORMAT}"
            clip.write_videofile(filename=str(video_file_path), logger=None, **settings.VIDEO_ENCODER_SETTINGS)
            logger.debug(f"Transform video {src_video.id}: saving")
            with video_file_path.open(mode='rb') as file:
                new_video = VideoFile(
                    id=video_id,
                    duration=clip.duration,
                    width=clip.size[0],
                    height=clip.size[1],
                    file=File(file, name=video_file_path.parts[-1]),
                )
                new_video.save()
    logger.info(f"Transform video {src_video.id}: finished")
    return new_video


@shared_task(ack_late=True)
def concatenate_videos(src_videos: List[VideoFile]) -> VideoFile:
    for video in src_videos:
        video.save(update_fields=('last_used_at',))

    if len(src_videos) == 1:
        return src_videos[0]
    src_videos_verb = '[' + ', '.join(video.id for video in src_videos) + ']'

    video_id = str(uuid.uuid4())

    logger.info(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): started")
    clips = [VideoFileClip(filename=video.file.path) for video in src_videos]
    try:
        with concatenate_videoclips(clips) as clip:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_dir_path = Path(tmp_dir)
                video_file_path = tmp_dir_path / f"{video_id}.{settings.VIDEO_OUTPUT_FORMAT}"
                clip.write_videofile(filename=str(video_file_path), logger=None, **settings.VIDEO_ENCODER_SETTINGS)
                logger.debug(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): saving")
                with video_file_path.open(mode='rb') as file:
                    new_video = VideoFile(
                        id=video_id,
                        duration=clip.duration,
                        width=clip.size[0],
                        height=clip.size[1],
                        file=File(file, name=video_file_path.parts[-1]),
                    )
                    new_video.save()
    finally:
        logger.debug(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): cleanup")
        for clip in clips:
            clip.close()
    logger.info(f"Concatenate videos {src_videos_verb} ({len(src_videos)}): finished")
    return new_video
