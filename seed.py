"""Populate the database with realistic sample data for development and testing.

Usage:
    python seed.py
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta

from config.database import create_tables, init_db
from models.category import Category
from models.chat_message import ChatMessage
from models.debt import Debt
from models.goal import Goal
from models.investment import Investment
from models.note import Note
from models.note_doodle import NoteDoodle
from models.note_image import NoteImage
from models.notebook import Notebook
from models.person import Person
from models.split import Split
from models.transaction import Transaction
from repositories.category_repository import CategoryRepository
from repositories.chat_message_repository import ChatMessageRepository
from repositories.debt_repository import DebtRepository
from repositories.goal_repository import GoalRepository
from repositories.investment_repository import InvestmentRepository
from repositories.note_doodle_repository import NoteDoodleRepository
from repositories.note_image_repository import NoteImageRepository
from repositories.note_repository import NoteRepository
from repositories.notebook_repository import NotebookRepository
from repositories.person_repository import PersonRepository
from repositories.split_repository import SplitRepository
from repositories.transaction_repository import TransactionRepository

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "database", "finance.db"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def d(offset: int) -> str:
    """Return an ISO date string offset days from today."""
    return (date.today() - timedelta(days=offset)).isoformat()


def ts(offset: int) -> str:
    """Return an ISO datetime string offset days from today."""
    return f"{d(offset)}T10:00:00"


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_categories(repo: CategoryRepository) -> dict[str, int]:
    """Insert default categories and return a name→id mapping."""
    defaults = [
        ("Food & Dining",   "restaurant",   "#FF6B6B", True),
        ("Transport",       "directions_car","#4ECDC4", True),
        ("Bills & Utilities","bolt",         "#45B7D1", True),
        ("Shopping",        "shopping_bag", "#96CEB4", True),
        ("Entertainment",   "movie",        "#FFEAA7", True),
        ("Health",          "favorite",     "#DDA0DD", True),
        ("Salary",          "payments",     "#98FB98", True),
        ("Freelance",       "laptop",       "#FFD700", True),
        ("Investments",     "trending_up",  "#87CEEB", True),
        ("Others",          "category",     "#D3D3D3", True),
    ]
    mapping: dict[str, int] = {}
    for name, icon, color, is_default in defaults:
        cat = repo.insert(Category(name=name, icon=icon, color=color, is_default=is_default))
        mapping[name] = cat.id
        print(f"  Category: {name}")
    return mapping


def seed_people(repo: PersonRepository) -> dict[str, int]:
    """Insert sample contacts and return a name→id mapping."""
    people_data = [
        ("Rahul Sharma",  "College friend"),
        ("Priya Mehta",   "Flatmate"),
        ("Amit Kumar",    "Office colleague"),
        ("Sneha Patel",   "Sister"),
    ]
    mapping: dict[str, int] = {}
    for name, notes in people_data:
        person = repo.insert(Person(name=name, notes=notes))
        mapping[name] = person.id
        print(f"  Person: {name}")
    return mapping


def seed_transactions(
    repo: TransactionRepository,
    cat: dict[str, int],
    people: dict[str, int],
) -> None:
    """Insert a mix of expense and income transactions."""
    rows = [
        (d(0),  450.0,  cat["Food & Dining"],    "Lunch at Subway",       "expense", None),
        (d(1),  1200.0, cat["Transport"],         "Uber to airport",       "expense", None),
        (d(1),  85000.0,cat["Salary"],            "July salary",           "income",  None),
        (d(2),  3500.0, cat["Shopping"],          "New headphones",        "expense", None),
        (d(2),  250.0,  cat["Food & Dining"],     "Coffee & snacks",       "expense", people["Rahul Sharma"]),
        (d(3),  1800.0, cat["Bills & Utilities"], "Electricity bill",      "expense", None),
        (d(3),  950.0,  cat["Entertainment"],     "Netflix + Spotify",     "expense", None),
        (d(4),  600.0,  cat["Health"],            "Pharmacy",              "expense", None),
        (d(5),  12000.0,cat["Freelance"],         "Logo design project",   "income",  None),
        (d(6),  780.0,  cat["Food & Dining"],     "Dinner with team",      "expense", people["Amit Kumar"]),
        (d(7),  2200.0, cat["Transport"],         "Monthly metro pass",    "expense", None),
        (d(8),  5000.0, cat["Bills & Utilities"], "Internet + mobile",     "expense", None),
        (d(10), 320.0,  cat["Food & Dining"],     "Breakfast",             "expense", None),
        (d(12), 15000.0,cat["Shopping"],          "Clothes shopping",      "expense", people["Priya Mehta"]),
        (d(15), 500.0,  cat["Entertainment"],     "Movie tickets",         "expense", people["Sneha Patel"]),
        (d(20), 85000.0,cat["Salary"],            "June salary",           "income",  None),
        (d(22), 1100.0, cat["Health"],            "Gym membership",        "expense", None),
        (d(25), 430.0,  cat["Food & Dining"],     "Grocery run",           "expense", None),
        (d(28), 8500.0, cat["Freelance"],         "Website maintenance",   "income",  None),
        (d(30), 2800.0, cat["Others"],            "Miscellaneous",         "expense", None),
    ]
    for tx_date, amount, cat_id, desc, tx_type, person_id in rows:
        repo.insert(Transaction(
            date=tx_date,
            amount=amount,
            category_id=cat_id,
            description=desc,
            transaction_type=tx_type,
            person_id=person_id,
        ))
        print(f"  Transaction: {desc} ({tx_type} ₹{amount})")


def seed_debts(repo: DebtRepository, people: dict[str, int]) -> None:
    """Insert sample debt records."""
    rows = [
        (people["Rahul Sharma"], 500.0,   "i_owe",   "Borrowed for lunch",      False),
        (people["Priya Mehta"],  3000.0,  "they_owe","Paid her electricity bill",False),
        (people["Amit Kumar"],   1200.0,  "i_owe",   "Movie and dinner",        False),
        (people["Sneha Patel"],  800.0,   "they_owe","Lent for auto fare",       True),
    ]
    for person_id, amount, direction, desc, settled in rows:
        repo.insert(Debt(
            person_id=person_id,
            amount=amount,
            direction=direction,
            description=desc,
            settled=settled,
        ))
        print(f"  Debt: {desc} ({direction} ₹{amount})")


def seed_splits(repo: SplitRepository, people: dict[str, int]) -> None:
    """Insert sample bill splits."""
    members = json.dumps([
        {"name": "Me",           "share": 875.0},
        {"name": "Rahul Sharma", "share": 875.0},
        {"name": "Priya Mehta",  "share": 875.0},
        {"name": "Amit Kumar",   "share": 875.0},
    ])
    repo.insert(Split(
        description="Team dinner at Barbeque Nation",
        total_amount=3500.0,
        date=d(3),
        members_json=members,
        my_share=875.0,
    ))
    print("  Split: Team dinner")

    members2 = json.dumps([
        {"name": "Me",           "share": 2500.0},
        {"name": "Priya Mehta",  "share": 2500.0},
    ])
    repo.insert(Split(
        description="Goa trip hotel",
        total_amount=5000.0,
        date=d(15),
        members_json=members2,
        my_share=2500.0,
    ))
    print("  Split: Goa trip hotel")


def seed_investments(repo: InvestmentRepository) -> None:
    """Insert sample investment holdings."""
    rows = [
        ("Reliance Industries",  "stock",   50000.0,  62000.0,  d(90)),
        ("Nifty 50 Index Fund",  "mutual_fund", 30000.0, 33500.0, d(180)),
        ("SBI Fixed Deposit",    "fd",      100000.0, 107000.0, d(365)),
        ("Bitcoin",              "crypto",  25000.0,  18000.0,  d(60)),
        ("HDFC Mid-Cap Fund",    "mutual_fund", 20000.0, 22800.0, d(120)),
    ]
    for name, inv_type, invested, current, inv_date in rows:
        repo.insert(Investment(
            name=name,
            investment_type=inv_type,
            amount_invested=invested,
            current_value=current,
            date=inv_date,
        ))
        print(f"  Investment: {name} (₹{invested} → ₹{current})")


def seed_goals(repo: GoalRepository) -> None:
    """Insert sample financial goals."""
    rows = [
        ("Emergency Fund",  "savings",  300000.0, 120000.0, d(-180), "#45B7D1"),
        ("New Laptop",      "gadgets",   80000.0,  45000.0, d(-60),  "#FFEAA7"),
        ("Goa Vacation",    "travel",    50000.0,  32000.0, d(-30),  "#96CEB4"),
        ("Home Down Payment","property",1000000.0,150000.0, d(-730), "#DDA0DD"),
    ]
    for name, category, target, current, deadline, color in rows:
        repo.insert(Goal(
            name=name,
            category=category,
            target_amount=target,
            current_amount=current,
            deadline=deadline,
            color=color,
        ))
        print(f"  Goal: {name} (₹{current}/₹{target})")


def seed_notebooks(repo: NotebookRepository) -> list[int]:
    """Insert sample notebooks and return their ids."""
    rows = [
        ("Personal Diary", "#96CEB4", "📔"),
        ("Work Ideas",     "#FFEAA7", "💡"),
    ]
    ids: list[int] = []
    for name, color, emoji in rows:
        nb = repo.insert(Notebook(name=name, color=color, emoji=emoji, created_at=ts(30)))
        ids.append(nb.id)
        print(f"  Notebook: {emoji} {name}")
    return ids


def seed_notes(
    note_repo: NoteRepository,
    image_repo: NoteImageRepository,
    doodle_repo: NoteDoodleRepository,
    notebook_ids: list[int],
) -> None:
    """Insert sample notes of all three types."""
    # Text notes
    n1 = note_repo.insert(Note(
        notebook_id=notebook_ids[0],
        title="Weekend Goals",
        content_text="- [ ] Go for a run\n- [x] Call mom\n- [ ] Read 30 pages",
        note_type="text",
        created_at=ts(2),
    ))
    print(f"  Note (text): Weekend Goals")

    # Image note (path is relative — no real file needed for seed)
    n2 = note_repo.insert(Note(
        notebook_id=notebook_ids[1],
        title="Whiteboard Sketch",
        content_text=None,
        note_type="image",
        created_at=ts(1),
    ))
    image_repo.insert(NoteImage(note_id=n2.id, image_path="note_images/sketch_001.jpg"))
    print(f"  Note (image): Whiteboard Sketch")


def seed_chat_messages(repo: ChatMessageRepository) -> None:
    """Insert a sample AI chat conversation."""
    messages = [
        ("user",  "What did I spend the most on this month?",          ts(1)),
        ("model", "Based on your transactions, your top spending categories this month are:\n1. Shopping — ₹18,500\n2. Bills & Utilities — ₹6,800\n3. Food & Dining — ₹2,005\n\nYou're currently ₹5,000 over your Food budget.", ts(1)),
        ("user",  "How much do I owe Rahul?",                           ts(0)),
        ("model", "You owe Rahul Sharma ₹500 for lunch. This debt is currently unsettled.", ts(0)),
    ]
    for role, content, timestamp in messages:
        repo.insert(ChatMessage(role=role, content=content, timestamp=timestamp))
        print(f"  ChatMessage ({role}): {content[:50]}...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Initialising database at: {DB_PATH}")
    init_db(DB_PATH)
    create_tables()
    print()

    print("Seeding categories...")
    cat_ids = seed_categories(CategoryRepository())

    print("\nSeeding people...")
    person_ids = seed_people(PersonRepository())

    print("\nSeeding transactions...")
    seed_transactions(TransactionRepository(), cat_ids, person_ids)

    print("\nSeeding debts...")
    seed_debts(DebtRepository(), person_ids)

    print("\nSeeding splits...")
    seed_splits(SplitRepository(), person_ids)

    print("\nSeeding investments...")
    seed_investments(InvestmentRepository())

    print("\nSeeding goals...")
    seed_goals(GoalRepository())

    print("\nSeeding notebooks...")
    nb_ids = seed_notebooks(NotebookRepository())

    print("\nSeeding notes...")
    seed_notes(NoteRepository(), NoteImageRepository(), NoteDoodleRepository(), nb_ids)

    print("\nSeeding chat messages...")
    seed_chat_messages(ChatMessageRepository())

    print("\nDone — database seeded successfully.")


if __name__ == "__main__":
    main()
