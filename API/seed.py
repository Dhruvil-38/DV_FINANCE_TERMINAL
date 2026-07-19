"""
Creates all tables and seeds demo data (idempotent — skips if users already exist).
Run automatically on API startup; can also run standalone: `python seed.py`.
"""

from datetime import datetime, timedelta
import random

from database import Base, engine, SessionLocal
import models
from auth import hash_password


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            return  # already seeded

        # ---------------- Clients ----------------
        clients = [
            models.Client(name="Meera Kulkarni", email="meera.k@example.com", phone="+91 98200 11223",
                          tier="Institutional", status="Active", assigned_analyst="R. Shah", aum=8_450_000),
            models.Client(name="Arjun Verma", email="arjun.verma@example.com", phone="+91 90000 44556",
                          tier="Premium", status="Active", assigned_analyst="R. Shah", aum=2_180_000),
            models.Client(name="Priya Nair", email="priya.nair@example.com", phone="+91 98765 33211",
                          tier="Standard", status="Onboarding", assigned_analyst="K. Rao", aum=340_000),
            models.Client(name="Karan Malhotra", email="karan.m@example.com", phone="+91 91234 88990",
                          tier="Premium", status="Active", assigned_analyst="K. Rao", aum=1_760_000),
            models.Client(name="Devika Iyer", email="devika.iyer@example.com", phone="+91 99887 12300",
                          tier="Standard", status="Dormant", assigned_analyst="R. Shah", aum=95_000),
        ]
        db.add_all(clients)
        db.flush()

        # ---------------- Users ----------------
        users = [
            models.User(name="Aditi Shah", email="admin@dvfinance.in",
                        hashed_password=hash_password("Admin@123"), role="admin"),
            models.User(name="Rohan Shah", email="analyst@dvfinance.in",
                        hashed_password=hash_password("Analyst@123"), role="analyst"),
            models.User(name="Kavya Rao", email="staff@dvfinance.in",
                        hashed_password=hash_password("Staff@123"), role="staff"),
            models.User(name=clients[0].name, email="client@dvfinance.in",
                        hashed_password=hash_password("Client@123"), role="client",
                        client_id=clients[0].id),
        ]
        db.add_all(users)
        db.flush()

        # ---------------- Watchlist ----------------
        watchlist = [
            ("NIFTY50", "Index", 24880.30, 0.42),
            ("BANKNIFTY", "Index", 52140.15, -0.18),
            ("RELIANCE", "Energy", 2985.40, 1.12),
            ("TCS", "Technology", 4120.75, 0.35),
            ("HDFCBANK", "Finance", 1652.90, -0.62),
            ("IRCTC", "Railway", 812.55, 2.31),
            ("ONGC", "Energy", 268.10, 0.88),
            ("INFY", "Technology", 1789.60, -0.24),
        ]
        db.add_all([
            models.WatchlistItem(symbol=s, sector=sec, last_price=p, day_change_pct=chg, added_by="Rohan Shah")
            for s, sec, p, chg in watchlist
        ])

        # ---------------- Trade calls ----------------
        sectors = ["Technology", "Finance", "Energy", "Railway"]
        statuses = ["ACTIVE", "TARGET_HIT", "SL_HIT", "CLOSED"]
        symbols = ["RELIANCE", "TCS", "HDFCBANK", "IRCTC", "ONGC", "INFY", "SBIN", "IRFC", "LT", "ADANIPORTS"]
        rng = random.Random(11)
        calls = []
        for i in range(28):
            entry = round(rng.uniform(200, 3000), 2)
            direction = rng.choice(["LONG", "SHORT"])
            sl_offset = entry * rng.uniform(0.01, 0.03)
            target_offset = entry * rng.uniform(0.02, 0.06)
            status = rng.choices(statuses, weights=[3, 4, 2, 2])[0]
            result_pct = None
            closed_at = None
            if status in ("TARGET_HIT", "SL_HIT", "CLOSED"):
                result_pct = round(rng.uniform(-3.5, 6.5), 2)
                closed_at = datetime.utcnow() - timedelta(days=rng.randint(0, 75))
            calls.append(models.TradeCall(
                symbol=rng.choice(symbols),
                sector=rng.choice(sectors),
                direction=direction,
                entry=entry,
                stop_loss=round(entry - sl_offset if direction == "LONG" else entry + sl_offset, 2),
                target=round(entry + target_offset if direction == "LONG" else entry - target_offset, 2),
                status=status,
                notes=rng.choice([
                    "Breakout confirmed on volume.", "Waiting for retest of support.",
                    "Sector rotation tailwind.", "Earnings catalyst priced in partially.",
                    "Tight stop given volatility.", "",
                ]),
                result_pct=result_pct,
                created_by=rng.choice(["Rohan Shah", "Kavya Rao"]),
                created_at=datetime.utcnow() - timedelta(days=rng.randint(1, 90)),
                closed_at=closed_at,
            ))
        db.add_all(calls)

        # ---------------- News ----------------
        news = [
            ("MARKET", "Nifty50 closes above 24,850 on banking strength",
             "Broader indices extended gains as banking and energy majors led the rally into the close.",
             "Market Desk"),
            ("MARKET", "Crude oil steadies near $82 amid supply concerns",
             "Energy counters remained in focus as global crude prices held firm through the session.",
             "Commodities Desk"),
            ("COMPANY", "Reliance Industries announces Q1 capex guidance",
             "Management reiterated its capital expenditure outlook for the retail and telecom verticals.",
             "Company Wire"),
            ("COMPANY", "IRCTC reports strong ticketing volume growth",
             "Passenger volumes rose meaningfully year-on-year, supporting the railway sector thesis.",
             "Company Wire"),
            ("FIRM", "DV Finance research desk expands sector coverage",
             "The desk has added dedicated coverage for the railway and infrastructure sub-sectors.",
             "DV Finance"),
            ("FIRM", "Quarterly client review sessions scheduled for next week",
             "Relationship managers will be reaching out to Premium and Institutional tier clients.",
             "DV Finance"),
        ]
        db.add_all([
            models.NewsItem(category=c, title=t, body=b, source=s, created_by="Kavya Rao",
                            published_at=datetime.utcnow() - timedelta(hours=rng.randint(1, 240)))
            for c, t, b, s in news
        ])

        # ---------------- Research notes ----------------
        notes = [
            models.ResearchNote(title="Institutional allocation review — Q2",
                                body="Recommend increasing energy sector weight given rotational flow signal.",
                                client_id=clients[0].id, created_by="Rohan Shah"),
            models.ResearchNote(title="Onboarding risk profile",
                                body="Moderate risk tolerance; prefers large-cap exposure only.",
                                client_id=clients[2].id, created_by="Kavya Rao"),
            models.ResearchNote(title="Technology sector — post-earnings note",
                                body="Margin commentary was softer than expected; trimming conviction.",
                                created_by="Rohan Shah"),
        ]
        db.add_all(notes)

        # ---------------- Tasks ----------------
        tasks = [
            models.Task(title="Prepare monthly performance report", status="IN_PROGRESS", priority="HIGH",
                       assigned_to="Kavya Rao", due_date=datetime.utcnow() + timedelta(days=2)),
            models.Task(title="Follow up with Priya Nair — onboarding docs", status="TODO", priority="MEDIUM",
                       assigned_to="Kavya Rao", due_date=datetime.utcnow() + timedelta(days=4)),
            models.Task(title="Review railway sector coverage note", status="TODO", priority="LOW",
                       assigned_to="Rohan Shah", due_date=datetime.utcnow() + timedelta(days=6)),
            models.Task(title="Compliance sweep — Q2 trade calls", status="DONE", priority="HIGH",
                       assigned_to="Aditi Shah", due_date=datetime.utcnow() - timedelta(days=3)),
        ]
        db.add_all(tasks)

        # ---------------- Documents ----------------
        docs = [
            models.Document(filename="Q2_Performance_Report.pdf", category="Research", size_kb=842,
                            uploaded_by="Kavya Rao"),
            models.Document(filename="Institutional_Client_Agreement.pdf", category="Compliance", size_kb=310,
                            uploaded_by="Aditi Shah", client_id=clients[0].id),
            models.Document(filename="Sector_Rotation_Playbook.pdf", category="Research", size_kb=1204,
                            uploaded_by="Rohan Shah"),
        ]
        db.add_all(docs)

        # ---------------- Notifications ----------------
        notifications = [
            models.Notification(audience_role=None, message="Market opens in 15 minutes — pre-market watchlist synced.", level="info"),
            models.Notification(audience_role="analyst", message="3 trade calls approaching target — review needed.", level="warning"),
            models.Notification(audience_role="client", message="Your Q2 performance report is now available.", level="success"),
            models.Notification(audience_role=None, message="Scheduled maintenance window: Sunday 02:00–03:00 IST.", level="info"),
        ]
        db.add_all(notifications)

        # ---------------- Engagement events ----------------
        events = []
        for c in clients:
            for _ in range(rng.randint(3, 14)):
                events.append(models.EngagementEvent(
                    client_id=c.id,
                    event_type=rng.choice(["LOGIN", "REPORT_VIEW", "DOWNLOAD", "MESSAGE"]),
                    created_at=datetime.utcnow() - timedelta(days=rng.randint(0, 60)),
                ))
        db.add_all(events)

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
