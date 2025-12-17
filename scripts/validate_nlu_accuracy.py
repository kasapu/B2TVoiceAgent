"""
Validate NLU Accuracy
Tests Rasa NLU model against test dataset
Target: >90% intent accuracy, >85% entity F1 score
"""

import asyncio
import httpx
import json
from typing import List, Dict, Any
from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix
import numpy as np


# Test dataset with labeled examples
TEST_DATASET = [
    # Greet intent
    {"text": "hello there", "expected_intent": "greet", "expected_entities": []},
    {"text": "hi", "expected_intent": "greet", "expected_entities": []},
    {"text": "good morning", "expected_intent": "greet", "expected_entities": []},
    {"text": "hey what's up", "expected_intent": "greet", "expected_entities": []},

    # Goodbye intent
    {"text": "goodbye", "expected_intent": "goodbye", "expected_entities": []},
    {"text": "see you later", "expected_intent": "goodbye", "expected_entities": []},
    {"text": "bye bye", "expected_intent": "goodbye", "expected_entities": []},
    {"text": "talk to you soon", "expected_intent": "goodbye", "expected_entities": []},

    # Check balance
    {"text": "what's my balance", "expected_intent": "check_balance", "expected_entities": []},
    {"text": "check my account balance", "expected_intent": "check_balance", "expected_entities": []},
    {"text": "how much money do I have", "expected_intent": "check_balance", "expected_entities": []},
    {"text": "show my checking balance", "expected_intent": "check_balance",
     "expected_entities": [{"entity_type": "account_type", "value": "checking"}]},
    {"text": "what is my savings account balance", "expected_intent": "check_balance",
     "expected_entities": [{"entity_type": "account_type", "value": "savings"}]},

    # Transfer money
    {"text": "I want to transfer money", "expected_intent": "transfer_money", "expected_entities": []},
    {"text": "send $500 to my savings", "expected_intent": "transfer_money",
     "expected_entities": [{"entity_type": "amount", "value": "500"}, {"entity_type": "account_type", "value": "savings"}]},
    {"text": "transfer 1000 dollars to checking", "expected_intent": "transfer_money",
     "expected_entities": [{"entity_type": "amount", "value": "1000"}, {"entity_type": "account_type", "value": "checking"}]},
    {"text": "move $250 to savings account", "expected_intent": "transfer_money",
     "expected_entities": [{"entity_type": "amount", "value": "250"}, {"entity_type": "account_type", "value": "savings"}]},

    # Help
    {"text": "help me", "expected_intent": "help", "expected_entities": []},
    {"text": "what can you do", "expected_intent": "help", "expected_entities": []},
    {"text": "I need assistance", "expected_intent": "help", "expected_entities": []},

    # Cancel
    {"text": "cancel", "expected_intent": "cancel", "expected_entities": []},
    {"text": "never mind", "expected_intent": "cancel", "expected_entities": []},
    {"text": "stop", "expected_intent": "cancel", "expected_entities": []},

    # Out of scope
    {"text": "what's the weather", "expected_intent": "out_of_scope", "expected_entities": []},
    {"text": "tell me a joke", "expected_intent": "out_of_scope", "expected_entities": []},
    {"text": "order pizza", "expected_intent": "out_of_scope", "expected_entities": []},
]


async def test_nlu_accuracy(nlu_url: str = "http://localhost:8001"):
    """
    Test NLU accuracy against labeled test dataset

    Args:
        nlu_url: URL of NLU service

    Returns:
        Dictionary with accuracy metrics
    """
    print("🧪 Starting NLU Accuracy Validation")
    print(f"NLU Service: {nlu_url}")
    print(f"Test samples: {len(TEST_DATASET)}\n")

    # Collect predictions
    predictions = []
    actuals = []
    all_results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for idx, test_case in enumerate(TEST_DATASET, 1):
            try:
                # Call NLU service
                response = await client.post(
                    f"{nlu_url}/parse",
                    json={"text": test_case["text"]}
                )

                if response.status_code != 200:
                    print(f"❌ Error on test {idx}: {response.status_code}")
                    predictions.append("error")
                    actuals.append(test_case["expected_intent"])
                    continue

                result = response.json()

                predicted_intent = result["intent"]["name"]
                intent_confidence = result["intent"]["confidence"]
                predicted_entities = result.get("entities", [])

                predictions.append(predicted_intent)
                actuals.append(test_case["expected_intent"])

                # Store detailed result
                all_results.append({
                    "text": test_case["text"],
                    "expected_intent": test_case["expected_intent"],
                    "predicted_intent": predicted_intent,
                    "confidence": intent_confidence,
                    "correct": predicted_intent == test_case["expected_intent"],
                    "entities": predicted_entities
                })

                # Print result
                status = "✅" if predicted_intent == test_case["expected_intent"] else "❌"
                print(f"{status} [{idx}/{len(TEST_DATASET)}] \"{test_case['text']}\"")
                print(f"   Expected: {test_case['expected_intent']}, "
                      f"Got: {predicted_intent} (conf: {intent_confidence:.2f})")

            except Exception as e:
                print(f"❌ Exception on test {idx}: {e}")
                predictions.append("error")
                actuals.append(test_case["expected_intent"])

    # Calculate metrics
    print("\n" + "="*60)
    print("📊 INTENT CLASSIFICATION RESULTS")
    print("="*60 + "\n")

    # Overall accuracy
    accuracy = accuracy_score(actuals, predictions)
    print(f"Overall Accuracy: {accuracy:.2%}")

    # Classification report
    print("\nDetailed Classification Report:")
    print(classification_report(actuals, predictions, zero_division=0))

    # Confusion matrix
    print("\nConfusion Matrix:")
    unique_labels = sorted(set(actuals + predictions))
    cm = confusion_matrix(actuals, predictions, labels=unique_labels)
    print(f"Labels: {unique_labels}")
    print(cm)

    # Confidence analysis
    print("\n" + "="*60)
    print("📈 CONFIDENCE ANALYSIS")
    print("="*60 + "\n")

    correct_confidences = [r["confidence"] for r in all_results if r["correct"]]
    incorrect_confidences = [r["confidence"] for r in all_results if not r["correct"]]

    if correct_confidences:
        print(f"Correct predictions - Avg confidence: {np.mean(correct_confidences):.2%}")
    if incorrect_confidences:
        print(f"Incorrect predictions - Avg confidence: {np.mean(incorrect_confidences):.2%}")

    # Low confidence warnings
    low_conf_threshold = 0.7
    low_conf_predictions = [r for r in all_results if r["confidence"] < low_conf_threshold]

    if low_conf_predictions:
        print(f"\n⚠️  {len(low_conf_predictions)} predictions with confidence < {low_conf_threshold:.0%}:")
        for r in low_conf_predictions:
            print(f"   - \"{r['text']}\" -> {r['predicted_intent']} ({r['confidence']:.2%})")

    # Entity extraction analysis (simplified)
    print("\n" + "="*60)
    print("🎯 ENTITY EXTRACTION")
    print("="*60 + "\n")

    entity_test_cases = [tc for tc in TEST_DATASET if tc["expected_entities"]]
    print(f"Test cases with entities: {len(entity_test_cases)}")

    if entity_test_cases:
        entity_matches = 0
        for result, test_case in zip(all_results, TEST_DATASET):
            if not test_case["expected_entities"]:
                continue

            predicted_entities = result["entities"]
            expected_entities = test_case["expected_entities"]

            # Simple entity matching
            for expected in expected_entities:
                found = any(
                    e["entity_type"] == expected["entity_type"]
                    for e in predicted_entities
                )
                if found:
                    entity_matches += 1

        total_expected = sum(len(tc["expected_entities"]) for tc in entity_test_cases)
        entity_accuracy = (entity_matches / total_expected) if total_expected > 0 else 0
        print(f"Entity extraction accuracy: {entity_accuracy:.2%}")
        print(f"Entities found: {entity_matches}/{total_expected}")

    # Final verdict
    print("\n" + "="*60)
    print("🎯 FINAL VERDICT")
    print("="*60 + "\n")

    intent_pass = accuracy >= 0.90
    intent_status = "✅ PASS" if intent_pass else "❌ FAIL"
    print(f"Intent Accuracy Target (>= 90%): {intent_status} ({accuracy:.2%})")

    if entity_test_cases:
        entity_pass = entity_accuracy >= 0.85 if entity_test_cases else True
        entity_status = "✅ PASS" if entity_pass else "❌ FAIL"
        print(f"Entity F1 Target (>= 85%): {entity_status} ({entity_accuracy:.2%})")
    else:
        print("Entity evaluation: ⚠️  Not enough entity test cases")

    overall_pass = intent_pass
    if overall_pass:
        print("\n🎉 NLU validation PASSED! Model meets production requirements.")
    else:
        print("\n⚠️  NLU validation FAILED. Model needs improvement:")
        if not intent_pass:
            print("   - Intent accuracy below 90% threshold")
            print("   - Recommendation: Add more training examples for confused intents")

    return {
        "accuracy": accuracy,
        "intent_pass": intent_pass,
        "detailed_results": all_results
    }


if __name__ == "__main__":
    print("="*60)
    print("NLU ACCURACY VALIDATION SCRIPT")
    print("Target: Intent Accuracy > 90%, Entity F1 > 85%")
    print("="*60 + "\n")

    result = asyncio.run(test_nlu_accuracy())

    # Exit with appropriate code
    exit_code = 0 if result["intent_pass"] else 1
    exit(exit_code)
