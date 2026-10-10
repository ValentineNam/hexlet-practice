"""Правила партнеров, общие для CSV-импорта и финального API."""

import re

MAX_INTEGER = 2147483647
PARTNER_TYPES = {'ООО', 'АО', 'ЗАО', 'ПАО', 'ИП'}
PARTNER_FIELDS = (
    'company_name', 'partner_type', 'inn', 'rating',
    'address', 'director', 'phone', 'email',
)


def clean_text(value):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ValueError('Текстовое поле должно содержать строку.')
    return ' '.join(value.split())


def validate_partner(payload):
    if not isinstance(payload, dict):
        raise ValueError('Ожидался JSON-объект с данными партнера.')
    partner = {
        field: clean_text(payload.get(field))
        for field in PARTNER_FIELDS if field != 'rating'
    }
    partner['partner_type'] = partner['partner_type'].upper()
    partner['email'] = partner['email'].lower()
    if not partner['company_name']:
        raise ValueError('Укажите наименование партнера.')
    if partner['partner_type'] not in PARTNER_TYPES:
        raise ValueError('Выберите корректный тип партнера.')
    if not re.fullmatch(r'(?:[0-9]{10}|[0-9]{12})', partner['inn']):
        raise ValueError('ИНН должен содержать 10 или 12 цифр.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', partner['email']):
        raise ValueError('Укажите корректный email.')
    for field, limit in (
        ('company_name', 255), ('email', 255), ('address', 500),
        ('director', 255), ('phone', 20),
    ):
        if len(partner[field]) > limit:
            raise ValueError(f'Поле {field}: максимум {limit} символов.')
    rating = payload.get('rating')
    if type(rating) is int:
        valid_rating = 0 <= rating <= MAX_INTEGER
    elif isinstance(rating, str) and re.fullmatch(r'0|[1-9][0-9]{0,9}', rating.strip()):
        rating = int(rating.strip())
        valid_rating = rating <= MAX_INTEGER
    else:
        valid_rating = False
    if not valid_rating:
        raise ValueError(f'Рейтинг должен быть целым числом от 0 до {MAX_INTEGER}.')
    partner['rating'] = rating
    for field in ('address', 'director', 'phone'):
        partner[field] = partner[field] or None
    return partner
