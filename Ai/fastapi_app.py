"""Single-file FastAPI application demonstrating common HTTP methods."""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="FastAPI CRUD Demo",
    description="A beginner API demonstrating GET, POST, PUT, PATCH, and DELETE.",
    version="2.0.0",
)


class ItemCreate(BaseModel):
    """Data required to create or completely replace an item."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(gt=0)
    available: bool = True


class ItemUpdate(BaseModel):
    """Optional fields accepted when partially updating an item."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, gt=0)
    available: bool | None = None


class Item(ItemCreate):
    """Stored item returned by the API."""

    id: int


items: dict[int, Item] = {}
next_item_id = 1


def find_item(item_id: int) -> Item:
    """Return an item or raise a standard HTTP 404 error."""
    item = items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/", summary="Welcome message", tags=["General"])
def read_root() -> dict[str, str]:
    """Return a simple welcome message."""
    return {"message": "Hello, FastAPI"}


@app.get("/greet/{name}", summary="Personalized greeting", tags=["General"])
def greet(name: str) -> dict[str, str]:
    """Return a greeting containing the name supplied in the URL."""
    return {"message": f"Hello, {name}", "name": name}


@app.get("/items", response_model=list[Item], summary="List items", tags=["Items"])
def list_items() -> list[Item]:
    """GET: Return every item currently held in memory."""
    return list(items.values())


@app.get("/items/{item_id}", response_model=Item, summary="Get an item", tags=["Items"])
def get_item(item_id: int) -> Item:
    """GET: Return one item by its numeric ID."""
    return find_item(item_id)


@app.post(
    "/items",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
    tags=["Items"],
)
def create_item(item_data: ItemCreate) -> Item:
    """POST: Create and return a new item."""
    global next_item_id

    item = Item(id=next_item_id, **item_data.model_dump())
    items[item.id] = item
    next_item_id += 1
    return item


@app.put("/items/{item_id}", response_model=Item, summary="Replace an item", tags=["Items"])
def replace_item(item_id: int, item_data: ItemCreate) -> Item:
    """PUT: Completely replace an existing item."""
    find_item(item_id)
    replacement = Item(id=item_id, **item_data.model_dump())
    items[item_id] = replacement
    return replacement


@app.patch("/items/{item_id}", response_model=Item, summary="Update an item", tags=["Items"])
def update_item(item_id: int, item_data: ItemUpdate) -> Item:
    """PATCH: Update only the supplied fields of an existing item."""
    current_item = find_item(item_id)
    changes = item_data.model_dump(exclude_unset=True, exclude_none=True)
    updated_item = current_item.model_copy(update=changes)
    items[item_id] = updated_item
    return updated_item


@app.delete("/items/{item_id}", summary="Delete an item", tags=["Items"])
def delete_item(item_id: int) -> dict[str, str | int]:
    """DELETE: Remove an existing item from memory."""
    find_item(item_id)
    del items[item_id]
    return {"message": "Item deleted", "item_id": item_id}
