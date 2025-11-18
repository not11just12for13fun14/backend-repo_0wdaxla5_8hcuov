import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI(title="E-Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateProductBody(Product):
    pass


class CreateOrderBody(Order):
    pass


@app.get("/")
def read_root():
    return {"message": "E-Commerce API running"}


@app.get("/api/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None, limit: int = 50):
    try:
        filter_dict = {}
        if category:
            filter_dict["category"] = category
        # Basic text search
        if q:
            filter_dict["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"category": {"$regex": q, "$options": "i"}},
            ]
        products = get_documents("product", filter_dict, limit)
        # Convert ObjectId to string
        for p in products:
            p["_id"] = str(p["_id"]) if "_id" in p else None
        return {"items": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products", status_code=201)
def create_product(body: CreateProductBody):
    try:
        pid = create_document("product", body)
        return {"id": pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    try:
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
        if not doc:
            raise HTTPException(404, "Product not found")
        doc["_id"] = str(doc["_id"]) if "_id" in doc else None
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orders", status_code=201)
def create_order(body: CreateOrderBody):
    try:
        # Optionally, compute totals server-side for trust
        subtotal = sum(item.price * item.quantity for item in body.items)
        total = subtotal + (body.shipping or 0)
        payload = body.model_dump()
        payload["subtotal"] = subtotal
        payload["total"] = total
        oid = create_document("order", payload)
        return {"id": oid, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
