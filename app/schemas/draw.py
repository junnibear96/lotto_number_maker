"""Schemas for lotto number drawing API."""

from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class DrawRequestSchema(Schema):
    exclude_mode = fields.String(
        required=True,
        validate=validate.OneOf(["NONE", "FIRST", "SECOND", "THIRD", "ALL"]),
    )

    exclude_numbers = fields.List(
        fields.Integer(validate=validate.Range(min=1, max=45)),
        required=False,
        load_default=None,
    )

    @validates_schema
    def _validate_exclude_numbers(self, data, **kwargs):  # type: ignore[no-untyped-def]
        nums = data.get("exclude_numbers")
        if nums is None:
            return

        if len(nums) != len(set(nums)):
            raise ValidationError({"exclude_numbers": ["Numbers must be unique"]})

        # Must leave at least 6 numbers available.
        if len(nums) > 39:
            raise ValidationError({"exclude_numbers": ["Too many excluded numbers (must be <= 39)"]})


class DrawResponseSchema(Schema):
    numbers = fields.List(fields.Integer(), required=True)
