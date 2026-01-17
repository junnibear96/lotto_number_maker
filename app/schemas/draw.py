"""Schemas for lotto number drawing API."""

from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class RangeFilterSchema(Schema):
    enabled = fields.Boolean(required=False, load_default=False)

    bucket = fields.String(
        required=False,
        load_default="1-10",
        validate=validate.OneOf(["1-10", "11-20", "21-30", "31-40", "41-45"]),
    )

    min_count = fields.Integer(required=False, load_default=0, validate=validate.Range(min=0, max=6))
    max_count = fields.Integer(required=False, load_default=6, validate=validate.Range(min=0, max=6))

    @validates_schema
    def _validate_min_max(self, data, **kwargs):  # type: ignore[no-untyped-def]
        if not data.get("enabled"):
            return
        mn = int(data.get("min_count") or 0)
        mx = int(data.get("max_count") or 0)
        if mn > mx:
            raise ValidationError({"min_count": ["min_count must be <= max_count"]})


class AdvancedOptionsSchema(Schema):
    consecutive_mode = fields.String(
        required=False,
        load_default="ALLOW",
        validate=validate.OneOf(["ALLOW", "REQUIRE", "FORBID"]),
    )

    last_digit_mode = fields.String(
        required=False,
        load_default="ALLOW",
        validate=validate.OneOf(["ALLOW", "FORBID"]),
    )

    range_filter = fields.Nested(RangeFilterSchema, required=False, load_default=lambda: {})

    max_previous_draw_overlap = fields.Integer(
        required=False,
        load_default=6,
        validate=validate.Range(min=0, max=6),
    )


class DrawRequestSchema(Schema):
    exclude_mode = fields.String(
        required=True,
        validate=validate.OneOf(["NONE", "FIRST", "SECOND", "THIRD", "ALL"]),
    )

    count = fields.Integer(
        required=False,
        load_default=1,
        validate=validate.Range(min=1, max=50),
    )

    exclude_numbers = fields.List(
        fields.Integer(validate=validate.Range(min=1, max=45)),
        required=False,
        load_default=None,
    )

    exclude_draws = fields.List(
        fields.List(
            fields.Integer(validate=validate.Range(min=1, max=45)),
            validate=validate.Length(equal=6),
        ),
        required=False,
        load_default=None,
        validate=validate.Length(max=200),
    )

    fixed_numbers = fields.List(
        fields.Integer(validate=validate.Range(min=1, max=45)),
        required=False,
        load_default=None,
    )

    advanced_options = fields.Nested(AdvancedOptionsSchema, required=False, load_default=lambda: {})

    @validates_schema
    def _validate_exclude_numbers(self, data, **kwargs):  # type: ignore[no-untyped-def]
        nums = data.get("exclude_numbers")
        fixed = data.get("fixed_numbers")
        exclude_draws = data.get("exclude_draws")

        if nums is not None:
            if len(nums) != len(set(nums)):
                raise ValidationError({"exclude_numbers": ["Numbers must be unique"]})

            # Must leave at least 6 numbers available.
            if len(nums) > 39:
                raise ValidationError({"exclude_numbers": ["Too many excluded numbers (must be <= 39)"]})

        if fixed is not None:
            if len(fixed) != len(set(fixed)):
                raise ValidationError({"fixed_numbers": ["Numbers must be unique"]})
            if len(fixed) > 2:
                raise ValidationError({"fixed_numbers": ["Too many fixed numbers (must be <= 2)"]})

        if nums is not None and fixed is not None:
            overlap = set(nums).intersection(set(fixed))
            if overlap:
                raise ValidationError({"fixed_numbers": ["Fixed numbers cannot overlap excluded numbers"]})

        if exclude_draws is not None:
            bad_idx: list[int] = []
            for i, draw in enumerate(exclude_draws):
                d = [int(x) for x in (draw or [])]
                if len(d) != 6 or len(set(d)) != 6:
                    bad_idx.append(i + 1)
            if bad_idx:
                raise ValidationError({"exclude_draws": [f"Each draw must be 6 unique numbers (bad items: {', '.join(str(i) for i in bad_idx)})"]})


class DrawResponseSchema(Schema):
    numbers = fields.List(fields.Integer(), required=True)

    # When count > 1, the response will also include multiple draws.
    draws = fields.List(fields.List(fields.Integer()), required=False)

    count = fields.Integer(required=False)
