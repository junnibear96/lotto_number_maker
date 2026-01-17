from marshmallow import Schema, fields

class LottoResultSchema(Schema):
    draw_no = fields.Int()
    numbers = fields.List(fields.Int())
    bonus_number = fields.Int()
