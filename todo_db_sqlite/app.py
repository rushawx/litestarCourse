from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from litestar import Litestar, get, post, put
from litestar.datastructures import State
from litestar.exceptions import ClientException, NotFoundException
from litestar.status_codes import HTTP_409_CONFLICT
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ToDoType = dict[str, Any]
TodoCollectionType = list[ToDoType]


class Base(DeclarativeBase):
    pass


class ToDoItem(Base):
    __tablename__ = "to_do_items"

    title: Mapped[str] = mapped_column(primary_key=True)
    done: Mapped[bool] = mapped_column(default=False)


def serialize_to_do(to_do: ToDoItem) -> ToDoType:
    return {"title": to_do.title, "done": to_do.done}


@asynccontextmanager
async def db_connection(app: Litestar) -> AsyncGenerator[None, None]:
    engine = getattr(app.state, "engine", None)
    if engine is None:
        engine = create_async_engine("sqlite+aiosqlite:///todo.sqlite", echo=True)
        app.state.engine = engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield
    finally:
        await engine.dispose()


sessionmaker = async_sessionmaker(expire_on_commit=False)


async def get_to_do_by_title(todo_name: str, session: AsyncSession) -> ToDoItem:
    query = select(ToDoItem).where(ToDoItem.title == todo_name)
    result = await session.execute(query)
    try:
        return result.scalars().one()
    except NoResultFound as e:
        raise NotFoundException(detail=f"TODO {todo_name!r} not found") from e


async def get_to_do_list(done: bool | None, session: AsyncSession) -> Sequence[ToDoItem]:
    query = select(ToDoItem)
    if done is not None:
        query = query.where(ToDoItem.done.is_(done))

    result = await session.execute(query)
    return result.scalars().all()


@get("/")
async def get_list(state: State, done: bool | None = None) -> TodoCollectionType:
    async with sessionmaker(bind=state.engine) as session:
        return [serialize_to_do(to_do) for to_do in await get_to_do_list(done, session)]


@post("/")
async def add_item(data: ToDoType, state: State) -> ToDoType:
    new_todo = ToDoItem(title=data["title"], done=data["done"])
    async with sessionmaker(bind=state.engine) as session:
        try:
            async with session.begin():
                session.add(new_todo)
        except IntegrityError as e:
            raise ClientException(
                status_code=HTTP_409_CONFLICT,
                detail=f"TODO {new_todo.title!r} already exists",
            ) from e

    return serialize_to_do(new_todo)


@put("/{item_title: str}")
async def update_item(item_title: str, data: ToDoType, state: State) -> ToDoType:
    async with sessionmaker(bind=state.engine) as session, session.begin():
        to_do_item = await get_to_do_by_title(item_title, session)
        to_do_item.title = data["title"]
        to_do_item.done = data["done"]
    return serialize_to_do(to_do_item)


app = Litestar([get_list, add_item, update_item], lifespan=[db_connection])


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
