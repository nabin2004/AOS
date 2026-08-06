"""VideoGeneration repository."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.video_generation import VideoGeneration


async def get_by_id(db: AsyncSession, generation_id: UUID) -> VideoGeneration | None:
    return await db.get(VideoGeneration, generation_id)


async def list_for_user(
    db: AsyncSession,
    *,
    user_id: UUID,
    conversation_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[VideoGeneration], int]:
    base = select(VideoGeneration).where(VideoGeneration.user_id == user_id)
    if conversation_id is not None:
        base = base.where(VideoGeneration.conversation_id == conversation_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                base.order_by(VideoGeneration.created_at.desc()).offset(skip).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


async def create(
    db: AsyncSession,
    *,
    user_id: UUID,
    conversation_id: UUID,
    prompt: str,
    mode: str,
    user_message_id: UUID | None = None,
    status: str = "pending",
) -> VideoGeneration:
    row = VideoGeneration(
        user_id=user_id,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        prompt=prompt,
        mode=mode,
        status=status,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def update(
    db: AsyncSession,
    generation: VideoGeneration,
    **fields: Any,
) -> VideoGeneration:
    for key, value in fields.items():
        if hasattr(generation, key):
            setattr(generation, key, value)
    await db.flush()
    await db.refresh(generation)
    return generation
