#!/usr/bin/env python3
"""
PB Daily Report Unit Conversion Validator
========================================

Validates unit conversions and metric completeness for PB Daily Report Slack messages.
Ensures GMV values are correctly converted to millions (백만원) and required metrics are present.

Created: 2025-09-29
Purpose: Fix unit conversion errors and metric completeness issues
"""

import re
import sys
from typing import Dict, List, Tuple, Optional

class UnitValidator:
    """Validates unit conversions and message structure for PB Daily Report."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def convert_to_millions(self, value: float) -> str:
        """
        Convert won amount to millions with proper formatting.

        Args:
            value: Amount in Korean won

        Returns:
            Formatted string in millions (e.g., "49.7")

        Examples:
            49,688,263원 → "49.7"
            219,792,681원 → "219.8"
            1,527,853원 → "1.5"
        """
        millions = value / 1_000_000
        if millions >= 10:
            return f"{millions:.1f}"
        elif millions >= 1:
            return f"{millions:.1f}"
        else:
            return f"{millions:.2f}"

    def validate_gmv_units(self, text: str) -> bool:
        """
        Validate that all GMV values use correct 백만 units.

        Args:
            text: Slack message content to validate

        Returns:
            True if all units are correct, False otherwise
        """
        # Check for incorrect usage of 억 (hundred million)
        incorrect_pattern = r'GMV\s+[\d,\.]+억'
        incorrect_matches = re.findall(incorrect_pattern, text)

        if incorrect_matches:
            self.errors.append(f"Found incorrect 억 units: {incorrect_matches}")
            return False

        # Check for correct usage of 백만 (million)
        correct_pattern = r'GMV\s+[\d,\.]+백만'
        correct_matches = re.findall(correct_pattern, text)

        # Check for GMV values without proper units
        raw_gmv_pattern = r'GMV\s+[\d,]+원'
        raw_matches = re.findall(raw_gmv_pattern, text)

        if raw_matches:
            self.warnings.append(f"Found raw GMV values that need conversion: {raw_matches}")

        return len(incorrect_matches) == 0

    def validate_required_metrics(self, text: str) -> bool:
        """
        Validate that required PB metrics are present in the message.

        Args:
            text: Slack message content to validate

        Returns:
            True if all required metrics are present, False otherwise
        """
        required_metrics = [
            (r'거래액비중:\s*\*?\*?[\d,\.]+%', "PB transaction ratio"),
            (r'MD2 SPV:\s*\*?\*?[\d,\.]+x', "MD2 SPV comparison")
        ]

        missing_metrics = []
        for pattern, name in required_metrics:
            if not re.search(pattern, text):
                missing_metrics.append(name)

        if missing_metrics:
            self.errors.append(f"Missing required metrics: {', '.join(missing_metrics)}")
            return False

        return True

    def validate_thread_units(self, text: str) -> bool:
        """
        Validate that brand thread messages use correct 백만 units.

        Args:
            text: Thread message content to validate

        Returns:
            True if all units are correct, False otherwise
        """
        # Check for incorrect usage of 억 in threads
        incorrect_thread_pattern = r'GMV\s+[\d,\.]+억'
        incorrect_matches = re.findall(incorrect_thread_pattern, text)

        if incorrect_matches:
            self.errors.append(f"Found incorrect 억 units in threads: {incorrect_matches}")
            return False

        # Check for correct 백만 format in threads
        correct_thread_pattern = r'GMV\s+[\d,\.]+백만'
        correct_matches = re.findall(correct_thread_pattern, text)

        # If there are GMV mentions but none with proper units
        gmv_mentions = re.findall(r'GMV\s+[\d,\.]+', text)
        if gmv_mentions and not correct_matches:
            self.warnings.append(f"Thread GMV values need proper 백만 units: {gmv_mentions}")

        return len(incorrect_matches) == 0

    def validate_top_products_format(self, text: str) -> bool:
        """
        Validate that Top 3 products section uses correct format with 백만 units.

        Args:
            text: Slack message content to validate

        Returns:
            True if format is correct, False otherwise
        """
        # Look for Top 3 products section
        top3_section = re.search(r'🏆 주요 상품 TOP 3.*?(?=\*\*🚨|\*\*📋)', text, re.DOTALL)

        if not top3_section:
            self.errors.append("Missing '주요 상품 TOP 3' section")
            return False

        top3_text = top3_section.group(0)

        # Check for correct format: GMV +X% | Y백만
        correct_format = r'GMV \+[\d,\.]+% \| [\d,\.]+백만'
        format_matches = re.findall(correct_format, top3_text)

        # Count expected products (should be 3)
        medal_count = len(re.findall(r'🥇|🥈|🥉', top3_text))

        if medal_count != 3:
            self.errors.append(f"Expected 3 products in TOP 3, found {medal_count}")
            return False

        if len(format_matches) != 3:
            self.errors.append("Top 3 products don't follow correct format with 백만 units")
            return False

        return True

    def validate_slack_message(self, content: str) -> Dict[str, any]:
        """
        Comprehensive validation of Slack message content.

        Args:
            content: Complete Slack message content

        Returns:
            Dictionary with validation results
        """
        self.errors = []
        self.warnings = []

        # Run all validations
        gmv_valid = self.validate_gmv_units(content)
        metrics_valid = self.validate_required_metrics(content)
        top3_valid = self.validate_top_products_format(content)
        thread_valid = self.validate_thread_units(content)

        return {
            'valid': gmv_valid and metrics_valid and top3_valid and thread_valid,
            'gmv_units_correct': gmv_valid,
            'required_metrics_present': metrics_valid,
            'top3_format_correct': top3_valid,
            'thread_units_correct': thread_valid,
            'errors': self.errors,
            'warnings': self.warnings
        }

    def get_conversion_examples(self) -> str:
        """
        Get examples of correct unit conversions.

        Returns:
            Formatted string with conversion examples
        """
        examples = [
            (49_688_263, "49.7"),
            (219_792_681, "219.8"),
            (1_527_853, "1.5"),
            (3_170_385, "3.2"),
            (3_375_706, "3.4")
        ]

        result = "Unit Conversion Examples:\n"
        result += "=" * 25 + "\n"

        for won_value, expected in examples:
            actual = self.convert_to_millions(won_value)
            status = "✅" if actual == expected else "❌"
            result += f"{won_value:,}원 → {actual}백만 {status}\n"

        return result

def main():
    """Command line interface for unit validation."""
    if len(sys.argv) != 2:
        print("Usage: python validate_units.py <slack_message_file>")
        print("       python validate_units.py --examples")
        sys.exit(1)

    validator = UnitValidator()

    if sys.argv[1] == "--examples":
        print(validator.get_conversion_examples())
        return

    # Read and validate Slack message file
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{sys.argv[1]}' not found")
        sys.exit(1)

    result = validator.validate_slack_message(content)

    # Print results
    print("PB Daily Report Message Validation")
    print("=" * 35)
    print(f"Overall Valid: {'✅' if result['valid'] else '❌'}")
    print(f"GMV Units: {'✅' if result['gmv_units_correct'] else '❌'}")
    print(f"Required Metrics: {'✅' if result['required_metrics_present'] else '❌'}")
    print(f"Top 3 Format: {'✅' if result['top3_format_correct'] else '❌'}")
    print(f"Thread Units: {'✅' if result['thread_units_correct'] else '❌'}")

    if result['errors']:
        print("\n❌ ERRORS:")
        for error in result['errors']:
            print(f"  - {error}")

    if result['warnings']:
        print("\n⚠️  WARNINGS:")
        for warning in result['warnings']:
            print(f"  - {warning}")

    if result['valid']:
        print("\n🎉 Message validation passed!")
    else:
        print(f"\n💥 Message validation failed with {len(result['errors'])} errors")
        sys.exit(1)

if __name__ == "__main__":
    main()