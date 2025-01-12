import uvicorn
from litestar import Litestar, get


@get("/hello/{name:str}")
async def print_hello(name: str) -> str:
    return f"Hello, {name}!\n"


app = Litestar(route_handlers=[print_hello])


if __name__ == "__main__":
    uvicorn.run(app)
