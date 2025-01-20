from dataclasses import dataclass

import litestar.exceptions
import uvicorn
from litestar import Litestar, get, post, put


@dataclass
class ToDoItem:
    title: str
    done: bool


TODO_LIST: list[ToDoItem] = [
    ToDoItem(title="Start writing TODO list", done=True),
    ToDoItem(title="???", done=False),
    ToDoItem(title="Profit", done=False),
]


@get("/show_list")
async def show_list(done: bool | None = None) -> list[ToDoItem]:
    if done is None:
        return TODO_LIST
    return [item for item in TODO_LIST if item.done == done]


@post("/append_list")
async def append_list(data: ToDoItem) -> list[ToDoItem]:
    TODO_LIST.append(data)
    return TODO_LIST


async def get_item_by_title(title: str) -> ToDoItem:
    for item in TODO_LIST:
        if item.title == title:
            return item
    raise litestar.exceptions.NotFoundException(detail=f"Item with title {title} not found")


@put("/update_item_by_title/{item_title:str}")
async def update_item_by_title(item_title: str, data: ToDoItem) -> ToDoItem:
    item = await get_item_by_title(title=item_title)
    item.title = data.title
    item.done = data.done
    return item


app = Litestar(route_handlers=[show_list, append_list, update_item_by_title])


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
