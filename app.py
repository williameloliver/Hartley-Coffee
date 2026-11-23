import json
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

app = Flask(__name__, static_folder="static")
database_url = os.environ.get("DATABASE_URL", "sqlite:///hartley_coffee.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db = SQLAlchemy(app)


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    recipe_grams = db.Column(db.Float, nullable=False, default=0)


class ComboComponent(db.Model):
    __tablename__ = "combo_components"
    id = db.Column(db.Integer, primary_key=True)
    combo_id = db.Column(db.String(80), db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    component_product_id = db.Column(db.String(80), db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)


class Sale(db.Model):
    __tablename__ = "sales"
    id = db.Column(db.String(80), primary_key=True)
    product_id = db.Column(db.String(80), db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    mode = db.Column(db.String(20), nullable=False, default="quick")
    created_at_ms = db.Column(db.BigInteger, nullable=False)


class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.String(80), primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    created_at_ms = db.Column(db.BigInteger, nullable=False)


class Inventory(db.Model):
    __tablename__ = "inventory"
    id = db.Column(db.Integer, primary_key=True)
    day_date = db.Column(db.String(10), nullable=False)
    start_cups = db.Column(db.String(40), nullable=False, default="")
    end_cups = db.Column(db.String(40), nullable=False, default="")
    start_grams = db.Column(db.String(40), nullable=False, default="")
    end_grams = db.Column(db.String(40), nullable=False, default="")
    notes = db.Column(db.Text, nullable=False, default="")


class ExtraStock(db.Model):
    __tablename__ = "extra_stock"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(80), db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    start_units = db.Column(db.String(40), nullable=False, default="")
    end_units = db.Column(db.String(40), nullable=False, default="")


def ensure_schema():
    with app.app_context():
        db.create_all()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "database": "unavailable"}), 503


def serialize_state():
    products = Product.query.order_by(Product.name).all()
    components = ComboComponent.query.all()
    by_combo = {}
    for c in components:
        by_combo.setdefault(c.combo_id, []).append({
            "productId": c.component_product_id,
            "qty": c.quantity
        })
    product_data = []
    for p in products:
        item = {"id": p.id, "name": p.name, "price": p.price, "type": p.type}
        if p.type == "coffee":
            item["recipeGrams"] = p.recipe_grams
        if p.type == "combo":
            item["components"] = by_combo.get(p.id, [])
        product_data.append(item)

    sales = [{
        "id": s.id, "productId": s.product_id, "name": s.product_name,
        "price": s.unit_price, "qty": s.quantity, "mode": s.mode, "ts": s.created_at_ms
    } for s in Sale.query.order_by(Sale.created_at_ms.desc()).all()]
    expenses = [{
        "id": e.id, "amount": e.amount, "description": e.description,
        "category": e.category, "ts": e.created_at_ms
    } for e in Expense.query.order_by(Expense.created_at_ms.desc()).all()]

    inv = Inventory.query.first()
    stock = {}
    for row in ExtraStock.query.all():
        stock[row.product_id] = {"start": row.start_units, "end": row.end_units}
    inventory = {
        "startCups": inv.start_cups if inv else "",
        "endCups": inv.end_cups if inv else "",
        "startGrams": inv.start_grams if inv else "",
        "endGrams": inv.end_grams if inv else "",
        "extraStock": stock,
        "notes": inv.notes if inv else ""
    }
    return {
        "brand": "Hartley Coffee",
        "dayDate": inv.day_date if inv else datetime.now().date().isoformat(),
        "products": product_data, "sales": sales, "expenses": expenses,
        "inventory": inventory
    }


@app.get("/api/state")
def get_state():
    if Product.query.count() == 0 and Sale.query.count() == 0 and Expense.query.count() == 0:
        return jsonify(None)
    return jsonify(serialize_state())


@app.put("/api/state")
def put_state():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Se esperaba un objeto JSON."}), 400
    products = payload.get("products", [])
    sales = payload.get("sales", [])
    expenses = payload.get("expenses", [])
    inventory = payload.get("inventory", {})
    if not all(isinstance(x, list) for x in (products, sales, expenses)):
        return jsonify({"error": "Productos, ventas y gastos deben ser listas."}), 400

    try:
        # Replace the current demo state in one transaction. The relational tables
        # remain normalized; combo components and inventory stock are separate rows.
        ComboComponent.query.delete()
        Sale.query.delete()
        Expense.query.delete()
        ExtraStock.query.delete()
        Product.query.delete()

        for p in products:
            if not p.get("id") or not p.get("name") or p.get("type") not in ("coffee", "extra", "combo"):
                raise ValueError("Producto inválido.")
            db.session.add(Product(
                id=str(p["id"]), name=str(p["name"])[:120],
                price=max(0, int(float(p.get("price", 0)))),
                type=p["type"], recipe_grams=float(p.get("recipeGrams", 0) or 0)
            ))
        db.session.flush()

        valid_product_ids = {str(p["id"]) for p in products}
        for p in products:
            if p.get("type") == "combo":
                for c in p.get("components", []):
                    component_id = str(c.get("productId", ""))
                    if component_id not in valid_product_ids or component_id == str(p["id"]):
                        raise ValueError("Componente de combo inválido.")
                    db.session.add(ComboComponent(
                        combo_id=str(p["id"]), component_product_id=component_id,
                        quantity=max(1, int(c.get("qty", 1)))
                    ))

        for s in sales:
            product_id = str(s.get("productId", ""))
            if product_id not in valid_product_ids:
                raise ValueError("Una venta referencia un producto inexistente.")
            db.session.add(Sale(
                id=str(s["id"]), product_id=product_id,
                product_name=str(s.get("name", ""))[:120],
                unit_price=max(0, int(float(s.get("price", 0)))),
                quantity=max(1, int(s.get("qty", 1))),
                mode=str(s.get("mode", "quick"))[:20],
                created_at_ms=int(s.get("ts", 0))
            ))

        for e in expenses:
            db.session.add(Expense(
                id=str(e["id"]), amount=max(0, int(float(e.get("amount", 0)))),
                description=str(e.get("description", ""))[:200],
                category=str(e.get("category", "Otros"))[:80],
                created_at_ms=int(e.get("ts", 0))
            ))

        inv = Inventory.query.first()
        if inv is None:
            inv = Inventory()
            db.session.add(inv)
        inv.day_date = str(payload.get("dayDate") or datetime.now().date().isoformat())[:10]
        inv.start_cups = str(inventory.get("startCups", ""))
        inv.end_cups = str(inventory.get("endCups", ""))
        inv.start_grams = str(inventory.get("startGrams", ""))
        inv.end_grams = str(inventory.get("endGrams", ""))
        inv.notes = str(inventory.get("notes", ""))[:5000]
        for product_id, stock in (inventory.get("extraStock") or {}).items():
            if str(product_id) in valid_product_ids:
                db.session.add(ExtraStock(
                    product_id=str(product_id),
                    start_units=str(stock.get("start", "")),
                    end_units=str(stock.get("end", ""))
                ))
        db.session.commit()
        return jsonify({"ok": True, "message": "Datos guardados en la base relacional."})
    except (ValueError, KeyError, TypeError) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "No se pudo guardar: revisa las relaciones entre productos, combos y ventas."}), 409
    except Exception:
        db.session.rollback()
        app.logger.exception("Error guardando estado")
        return jsonify({"error": "Error interno al guardar los datos."}), 500


@app.get("/api/schema")
def schema_info():
    return jsonify({
        "tables": ["products", "combo_components", "sales", "expenses", "inventory", "extra_stock"],
        "database_engine": db.engine.dialect.name
    })


ensure_schema()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
