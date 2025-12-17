"""
Migrate PostgreSQL training data to Rasa NLU format
Converts training_examples from database to Rasa YAML format with entity annotations
"""

import asyncio
import asyncpg
import yaml
import os
from typing import Dict, List, Any
import re


async def fetch_training_data(conn) -> List[Dict[str, Any]]:
    """Fetch training examples from PostgreSQL"""
    query = """
        SELECT
            i.intent_name,
            te.example_text,
            te.annotated_entities,
            te.language
        FROM intents i
        JOIN training_examples te ON i.intent_id = te.intent_id
        WHERE i.is_active = TRUE
        ORDER BY i.intent_name, te.example_id
    """

    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


def add_entity_annotations(text: str, entities: Dict[str, Any]) -> str:
    """
    Add entity annotations to text in Rasa format
    Example: "Transfer [500](amount) to [savings](account_type)"
    """
    if not entities or not isinstance(entities, dict):
        return f"- {text}"

    # If entities dict is empty, return plain text
    if not entities:
        return f"- {text}"

    # For now, return plain text - we'll add annotations manually
    # in the enhanced training data
    return f"- {text}"


def create_annotated_examples() -> Dict[str, List[str]]:
    """
    Create entity-annotated training examples
    Uses Rasa's annotation format: [entity_value](entity_type)
    """
    return {
        "greet": [
            "- hello",
            "- hi",
            "- hey",
            "- good morning",
            "- good afternoon",
            "- greetings",
        ],
        "goodbye": [
            "- bye",
            "- goodbye",
            "- see you later",
            "- talk to you soon",
            "- have a good day",
        ],
        "check_balance": [
            "- what is my balance",
            "- check my balance",
            "- how much money do I have",
            "- what's my [checking](account_type) balance",
            "- show me my [savings](account_type) account balance",
            "- balance inquiry",
            "- tell me my account balance",
        ],
        "transfer_money": [
            "- I want to transfer money",
            "- send money",
            "- transfer [500](amount) to my [savings](account_type)",
            "- send [$1000](amount) to [checking](account_type)",
            "- I need to make a transfer",
            "- transfer [100 dollars](amount) to [savings](account_type) account",
        ],
        "help": [
            "- help",
            "- what can you do",
            "- help me",
            "- I need assistance",
            "- can you assist me",
        ],
        "cancel": [
            "- cancel",
            "- stop",
            "- nevermind",
            "- forget it",
            "- don't do that",
        ],
        "out_of_scope": [
            "- what's the weather",
            "- tell me a joke",
            "- order pizza",
            "- play music",
        ]
    }


async def migrate_to_rasa():
    """Main migration function"""
    print("🚀 Starting migration from PostgreSQL to Rasa NLU format...")

    # Connect to database
    try:
        conn = await asyncpg.connect(
            "postgresql://ocpuser:ocppassword@localhost:5432/ocplatform"
        )
        print("✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("⚠️  Using fallback annotated examples only")
        conn = None

    # Fetch existing data if connection successful
    intent_examples = {}

    if conn:
        try:
            rows = await fetch_training_data(conn)
            print(f"📊 Fetched {len(rows)} training examples from database")

            # Group by intent
            for row in rows:
                intent = row['intent_name']
                text = row['example_text']
                entities = row.get('annotated_entities')

                if intent not in intent_examples:
                    intent_examples[intent] = []

                formatted = add_entity_annotations(text, entities)
                intent_examples[intent].append(formatted)

            await conn.close()
            print("✅ Database connection closed")

        except Exception as e:
            print(f"⚠️  Error fetching data: {e}")
            if conn:
                await conn.close()

    # Merge with annotated examples (entity-rich examples take priority)
    annotated_examples = create_annotated_examples()

    for intent, examples in annotated_examples.items():
        if intent in intent_examples:
            # Merge, avoiding duplicates
            existing_texts = {ex.replace("- ", "").split("[")[0].strip()
                            for ex in intent_examples[intent]}
            for example in examples:
                example_text = example.replace("- ", "").split("[")[0].strip()
                if example_text not in existing_texts:
                    intent_examples[intent].append(example)
        else:
            intent_examples[intent] = examples

    # Build Rasa NLU data structure
    nlu_data = {
        "version": "3.1",
        "nlu": []
    }

    for intent, examples in sorted(intent_examples.items()):
        nlu_data["nlu"].append({
            "intent": intent,
            "examples": "\n".join(examples)
        })

    # Write to file
    output_path = "/home/kranti/OCPplatform/services/nlu-service/rasa_config/data/nlu.yml"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(nlu_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"✅ Migration complete!")
    print(f"📁 Training data written to: {output_path}")
    print(f"📊 Total intents: {len(intent_examples)}")
    print(f"📊 Total examples: {sum(len(examples) for examples in intent_examples.values())}")

    # Print summary
    print("\n📋 Intent Summary:")
    for intent, examples in sorted(intent_examples.items()):
        entity_count = sum(1 for ex in examples if "[" in ex and "](" in ex)
        print(f"  - {intent}: {len(examples)} examples ({entity_count} with entities)")


if __name__ == "__main__":
    asyncio.run(migrate_to_rasa())
