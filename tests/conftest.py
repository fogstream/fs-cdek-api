from random import randint

import pytest

from cdek.api import CDEKClient
from cdek.entities import DeliveryRequest


delivery_type_list = [
    {
        'recipient_address': {'pvz_code': 'XAB1'},
        'tariff_type_code': 138,
        'shipping_price': 300.0,
    },
    {
        'recipient_address': {'street': 'Ленина', 'house': '50', 'flat': '31'},
        'tariff_type_code': 139,
        'shipping_price': 0,
    },
]


@pytest.fixture(params=delivery_type_list, ids=['PVZ', 'DOOR'])
def delivery_type(request):
    return request.param


@pytest.fixture
def cdek_client():
    return CDEKClient(
        account='z9GRRu7FxmO53CQ9cFfI6qiy32wpfTkd',
        secure_password='w24JTCv4MnAcuRTx0oHjHLDtyt3I6IBq',
        api_url='http://integration.edu.cdek.ru',
        test=True,
    )


# pylint: disable=redefined-outer-name
@pytest.fixture
def delivery_request(delivery_type):
    delivery_request_obj = DeliveryRequest(number='12345678')
    order = delivery_request_obj.add_order(
        number=randint(100000, 1000000),
        recipient_name='Иванов Иван Иванович',
        phone='+79999999999',
        send_city_post_code='680000',
        rec_city_post_code='680000',
        seller_name='Магазин',
        comment='Духи',
        tariff_type_code=delivery_type['tariff_type_code'],
        shipping_price=delivery_type['shipping_price'],
    )
    delivery_request_obj.add_address(
        order, **delivery_type['recipient_address'])
    package = delivery_request_obj.add_package(
        order_element=order,
        size_a=10,
        size_b=10,
        size_c=10,
        number=randint(100000, 1000000),
        barcode=randint(100000, 1000000),
        weight=600,
    )
    delivery_request_obj.add_item(
        package_element=package,
        weight=500,
        cost=1000,
        ware_key='12345678',
        comment='Духи',
    )

    return delivery_request_obj
