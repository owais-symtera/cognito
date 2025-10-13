"""
Database seed script for Technology Go/No-Go Scoring Matrix
Based on Technology_Go_NoGo_Scoring_Detailed_MAIN.md
"""

import asyncio
import asyncpg
import structlog

logger = structlog.get_logger(__name__)


async def seed_technology_scoring_matrix():
    """Seed the Technology Go/No-Go scoring matrix data"""

    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='cognito-engine'
    )

    try:
        # Create tables if they don't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scoring_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                weightage DECIMAL(5,2) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scoring_parameters (
                id SERIAL PRIMARY KEY,
                category_id INTEGER REFERENCES scoring_categories(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                unit VARCHAR(50),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scoring_ranges (
                id SERIAL PRIMARY KEY,
                parameter_id INTEGER REFERENCES scoring_parameters(id) ON DELETE CASCADE,
                delivery_method VARCHAR(50) NOT NULL,
                score INTEGER NOT NULL,
                min_value DECIMAL(10,2),
                max_value DECIMAL(10,2),
                range_text VARCHAR(100),
                is_exclusion BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT check_delivery_method CHECK (delivery_method IN ('Transdermal', 'Transmucosal', 'Both'))
            )
        """)

        logger.info("Tables created successfully")

        # Clear existing data
        await conn.execute("DELETE FROM scoring_ranges")
        await conn.execute("DELETE FROM scoring_parameters")
        await conn.execute("DELETE FROM scoring_categories")

        logger.info("Cleared existing scoring data")

        # Seed categories with weightages
        categories_data = [
            ("Technology Go/No-Go", 40.0, "Dose-based scoring for drug delivery feasibility"),
            ("Molecular Weight", 30.0, "Molecular weight impact on drug delivery"),
            ("API Characteristics", 20.0, "Active Pharmaceutical Ingredient melting point characteristics"),
            ("Log P", 10.0, "Partition coefficient for lipophilicity assessment"),
        ]

        category_ids = {}
        for name, weightage, description in categories_data:
            cat_id = await conn.fetchval(
                """
                INSERT INTO scoring_categories (name, weightage, description)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                name, weightage, description
            )
            category_ids[name] = cat_id
            logger.info(f"Inserted category: {name} (ID: {cat_id})")

        # Seed parameters
        parameters_data = [
            (category_ids["Technology Go/No-Go"], "Dose", "mg/kg/day", "Daily dose per kilogram body weight"),
            (category_ids["Molecular Weight"], "Molecular Weight", "Da", "Molecular weight in Daltons"),
            (category_ids["API Characteristics"], "Melting Point", "°C", "Melting point in Celsius"),
            (category_ids["Log P"], "Log P", "", "Partition coefficient (octanol-water)"),
        ]

        parameter_ids = {}
        for cat_id, name, unit, description in parameters_data:
            param_id = await conn.fetchval(
                """
                INSERT INTO scoring_parameters (category_id, name, unit, description)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                cat_id, name, unit, description
            )
            parameter_ids[name] = param_id
            logger.info(f"Inserted parameter: {name} (ID: {param_id})")

        # Seed scoring ranges for Dose (mg/kg/day)
        dose_ranges = [
            # Transdermal
            (parameter_ids["Dose"], "Transdermal", 9, None, 0, "≤0", False),
            (parameter_ids["Dose"], "Transdermal", 8, 1, 2, "1–2", False),
            (parameter_ids["Dose"], "Transdermal", 7, 3, 5, "3–5", False),
            (parameter_ids["Dose"], "Transdermal", 6, 6, 8, "6–8", False),
            (parameter_ids["Dose"], "Transdermal", 5, 9, 11, "9–11", False),
            (parameter_ids["Dose"], "Transdermal", 4, 12, 15, "12–15", False),
            (parameter_ids["Dose"], "Transdermal", 3, 16, 18, "16–18", False),
            (parameter_ids["Dose"], "Transdermal", 2, 19, 22, "19–22", False),
            (parameter_ids["Dose"], "Transdermal", 1, 23, 30, "23–30", False),
            (parameter_ids["Dose"], "Transdermal", 0, 31, 50, "31–50", False),
            (parameter_ids["Dose"], "Transdermal", 0, 50, None, ">50", True),
            # Transmucosal
            (parameter_ids["Dose"], "Transmucosal", 9, None, 0, "≤0", False),
            (parameter_ids["Dose"], "Transmucosal", 8, 1, 2, "1–2", False),
            (parameter_ids["Dose"], "Transmucosal", 7, 3, 5, "3–5", False),
            (parameter_ids["Dose"], "Transmucosal", 6, 6, 10, "6–10", False),
            (parameter_ids["Dose"], "Transmucosal", 5, 11, 15, "11–15", False),
            (parameter_ids["Dose"], "Transmucosal", 4, 16, 20, "16–20", False),
            (parameter_ids["Dose"], "Transmucosal", 3, 21, 30, "21–30", False),
            (parameter_ids["Dose"], "Transmucosal", 2, 31, 40, "31–40", False),
            (parameter_ids["Dose"], "Transmucosal", 1, 41, 50, "41–50", False),
            (parameter_ids["Dose"], "Transmucosal", 0, 51, 70, "51–70", False),
            (parameter_ids["Dose"], "Transmucosal", 0, 70, None, ">70", True),
        ]

        # Seed scoring ranges for Molecular Weight (Da)
        mw_ranges = [
            # Transdermal
            (parameter_ids["Molecular Weight"], "Transdermal", 9, None, 199, "≤199", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 8, 200, 249, "200–249", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 7, 250, 299, "250–299", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 6, 300, 349, "300–349", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 5, 350, 399, "350–399", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 4, 400, 449, "400–449", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 3, 450, 499, "450–499", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 2, 500, 549, "500–549", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 1, 550, 599, "550–599", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 0, 600, 800, "600–800", False),
            (parameter_ids["Molecular Weight"], "Transdermal", 0, 800, None, ">800", True),
            # Transmucosal
            (parameter_ids["Molecular Weight"], "Transmucosal", 9, None, 199, "≤199", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 8, 200, 299, "200–299", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 7, 300, 399, "300–399", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 6, 400, 599, "400–599", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 5, 600, 999, "600–999", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 4, 1000, 1999, "1000–1999", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 3, 2000, 2999, "2000–2999", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 2, 3000, 3999, "3000–3999", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 1, 4000, 4999, "4000–4999", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 0, 5000, 10000, "5000–10000", False),
            (parameter_ids["Molecular Weight"], "Transmucosal", 0, 10000, None, ">10000", True),
        ]

        # Seed scoring ranges for Melting Point (°C) - Same for both delivery methods
        mp_ranges = [
            (parameter_ids["Melting Point"], "Both", 9, None, 49, "≤49", False),
            (parameter_ids["Melting Point"], "Both", 8, 50, 89, "50–89", False),
            (parameter_ids["Melting Point"], "Both", 7, 90, 129, "90–129", False),
            (parameter_ids["Melting Point"], "Both", 6, 130, 169, "130–169", False),
            (parameter_ids["Melting Point"], "Both", 5, 170, 209, "170–209", False),
            (parameter_ids["Melting Point"], "Both", 4, 210, 249, "210–249", False),
            (parameter_ids["Melting Point"], "Both", 3, 250, 279, "250–279", False),
            (parameter_ids["Melting Point"], "Both", 2, 280, 309, "280–309", False),
            (parameter_ids["Melting Point"], "Both", 1, 310, 339, "310–339", False),
            (parameter_ids["Melting Point"], "Both", 0, 340, 380, "340–380", False),
            (parameter_ids["Melting Point"], "Both", 0, 380, None, ">380", True),
        ]

        # Seed scoring ranges for Log P
        # Note: Log P has special non-continuous ranges
        logp_ranges = [
            # Transdermal
            (parameter_ids["Log P"], "Transdermal", 9, 1, 2, "1–2", False),
            (parameter_ids["Log P"], "Transdermal", 7, 3, 3, "3", False),
            (parameter_ids["Log P"], "Transdermal", 5, 4, 5, "4–5", False),
            (parameter_ids["Log P"], "Transdermal", 5, 0, 1, "0–1", False),
            (parameter_ids["Log P"], "Transdermal", 3, 6, 6, "6", False),
            (parameter_ids["Log P"], "Transdermal", 0, None, 0, "<0", False),
            (parameter_ids["Log P"], "Transdermal", 0, 6, None, "≥6", False),
            # Transmucosal
            (parameter_ids["Log P"], "Transmucosal", 9, 1.6, 3.2, "1.6–3.2", False),
            (parameter_ids["Log P"], "Transmucosal", 6, 1, 1.5, "1–1.5", False),
            (parameter_ids["Log P"], "Transmucosal", 6, 3.3, 4, "3.3–4", False),
            (parameter_ids["Log P"], "Transmucosal", 3, 0, 0.9, "0–0.9", False),
            (parameter_ids["Log P"], "Transmucosal", 3, 5, 5, "5", False),
            (parameter_ids["Log P"], "Transmucosal", 0, None, 0, "<0", False),
            (parameter_ids["Log P"], "Transmucosal", 0, 6, None, "≥6", False),
        ]

        # Insert all ranges
        all_ranges = dose_ranges + mw_ranges + mp_ranges + logp_ranges

        for param_id, delivery, score, min_val, max_val, range_text, is_excl in all_ranges:
            await conn.execute(
                """
                INSERT INTO scoring_ranges
                (parameter_id, delivery_method, score, min_value, max_value, range_text, is_exclusion)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                param_id, delivery, score, min_val, max_val, range_text, is_excl
            )

        logger.info(f"Inserted {len(all_ranges)} scoring ranges")

        # Verify data
        total_categories = await conn.fetchval("SELECT COUNT(*) FROM scoring_categories")
        total_parameters = await conn.fetchval("SELECT COUNT(*) FROM scoring_parameters")
        total_ranges = await conn.fetchval("SELECT COUNT(*) FROM scoring_ranges")

        logger.info(f"Seed complete: {total_categories} categories, {total_parameters} parameters, {total_ranges} ranges")

    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_technology_scoring_matrix())
