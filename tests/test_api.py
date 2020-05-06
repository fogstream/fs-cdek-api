# -*- coding: utf-8 -*-
from __future__ import unicode_literals
try:
    from contextlib import ExitStack as does_not_raise
except ImportError:
    from contextlib2 import ExitStack as does_not_raise
import datetime
from typing import Dict

import pytest

from cdek.api import CDEKClient
from cdek.entities import CallCourier, PreAlert


def test_get_regions(cdek_client):
    regions = cdek_client.get_regions(region_code_ext=27)

    assert regions
    assert regions[0]['countryCode'] == 'RU'
    assert regions[0]['regionName'] == 'Хабаровский'


def test_get_cities(cdek_client):
    cities = cdek_client.get_cities(region_code_ext=27)

    assert cities
    assert cities[0]['countryCode'] == 'RU'
    assert cities[0]['region'] == 'Хабаровский'


def test_get_pvz_list(cdek_client):
    response = cdek_client.get_delivery_points(city_post_code=680000)

    assert response
    assert 'pvz' in response
    pvz_list = response['pvz']
    assert pvz_list
    assert pvz_list[0]['city'] == 'Хабаровск'


def test_order_creation(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'DispatchNumber' in order
    assert 'Number' in order


def test_order_info(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'DispatchNumber' in order
    assert 'Number' in order

    dispatch_number = order['DispatchNumber']

    info = cdek_client.get_orders_info([dispatch_number])

    assert info
    assert len(info) == 1
    order_info = info[0]
    assert 'ErrorCode' not in order_info
    assert order_info['DispatchNumber'] == dispatch_number


def test_order_status_info(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'DispatchNumber' in order
    assert 'Number' in order

    dispatch_number = order['DispatchNumber']

    statuses = cdek_client.get_orders_statuses([dispatch_number])

    assert statuses
    assert len(statuses) == 1
    status_info = statuses[0]
    assert 'ErrorCode' not in status_info
    assert status_info['DispatchNumber'] == dispatch_number
    assert status_info['Status']['Code'] == '1'  # Создан


def test_courier_call(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'DispatchNumber' in order
    assert 'Number' in order

    dispatch_number = order['DispatchNumber']

    next_day = datetime.date.today() + datetime.timedelta(days=1)

    call_courier = CallCourier()
    call_request = call_courier.add_call(
        date=next_day,
        dispatch_number=dispatch_number,
        sender_phone='+79999999999',
        time_begin=datetime.time(hour=10),
        time_end=datetime.time(hour=17),
    )
    call_courier.add_address(
        call_element=call_request,
        address_street='Пушкина',
        address_house='50',
        address_flat='1',
    )

    call = cdek_client.call_courier(call_courier)

    assert call
    assert 'Number' in call


def test_courier_call_with_lunch(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'ErrorCode' not in order
    assert 'DispatchNumber' in order
    assert 'Number' in order

    dispatch_number = order['DispatchNumber']

    next_day = datetime.date.today() + datetime.timedelta(days=1)

    call_courier = CallCourier()
    call_request = call_courier.add_call(
        date=next_day,
        dispatch_number=dispatch_number,
        sender_phone='+79999999999',
        time_begin=datetime.time(hour=10),
        time_end=datetime.time(hour=17),
        lunch_begin=datetime.time(hour=13),
        lunch_end=datetime.time(hour=14),
    )
    call_courier.add_address(
        call_element=call_request,
        address_street='Пушкина',
        address_house='50',
        address_flat='1',
    )

    call = cdek_client.call_courier(call_courier)

    assert call
    assert 'Number' in call


def test_print_orders(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'ErrorCode' not in order
    assert 'DispatchNumber' in order
    assert 'Number' in order

    dispatch_number = order['DispatchNumber']

    order_print = cdek_client.get_orders_print([dispatch_number])

    assert order_print is not None


@pytest.mark.skip(
    reason="The cause if the error isn't clear: "
           "fail creating pdf on the cdek side."
)
def test_print_barcode(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'ErrorCode' not in order
    assert 'DispatchNumber' in order
    assert 'Number' in order

    dispatch_number = order['DispatchNumber']

    barcode_print = cdek_client.get_barcode_print([dispatch_number])

    assert barcode_print is not None


@pytest.mark.parametrize('tariff,expectation', [
    pytest.param({'tariff_id': 3}, does_not_raise(), id='Single tariff'),
    pytest.param({'tariffs': [3, 1]}, does_not_raise(), id='Multiple tariffs'),
    pytest.param({}, pytest.raises(AttributeError), marks=pytest.mark.xfail,
                 id='Without tariffs')])
def test_shipping_cost_calculator(cdek_client, tariff,
                                  expectation):
    with expectation:
        shipping_costs = cdek_client.get_shipping_cost(
            sender_city_id=270,
            receiver_city_id=44,
            goods=[
                {'weight': 0.3, 'length': 10, 'width': 7, 'height': 5},
                {'weight': 0.1, 'volume': 0.1},
            ],
            services=[{'id': 2, 'param': 1000}],
            **tariff
        )

        assert shipping_costs
        assert 'error' not in shipping_costs
        assert 'result' in shipping_costs
        result = shipping_costs['result']
        assert result['tariffId'] == 3


def test_shipping_cost_with_auth_data(cdek_client):
    cdek_client._test = False

    shipping_costs = cdek_client.get_shipping_cost(
        sender_city_id=270,
        receiver_city_id=44,
        goods=[
            {'weight': 0.3, 'length': 10, 'width': 7, 'height': 5},
            {'weight': 0.1, 'volume': 0.1},
        ],
        tariff_id=136,  # Для тарифов ИМ требуются валидные данные входа ИМ
    )

    assert 'error' in shipping_costs


def test_order_delete(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'DispatchNumber' in order
    assert 'Number' in order

    dispatch_number = order['DispatchNumber']

    statuses = cdek_client.get_orders_statuses([dispatch_number])

    assert statuses
    assert len(statuses) == 1
    status_info = statuses[0]
    assert 'ErrorCode' not in order
    assert status_info['DispatchNumber'] == dispatch_number
    assert status_info['Status']['Code'] == '1'  # Создан
    assert 'ActNumber' in status_info
    act_number = status_info['ActNumber']

    delete_requests = cdek_client.delete_orders(
        act_number=act_number,
        dispatch_numbers=[dispatch_number],
    )

    assert delete_requests
    assert len(delete_requests) == 1
    deleted_order = delete_requests[0]
    assert 'DispatchNumber' in deleted_order
    assert deleted_order['DispatchNumber'] == dispatch_number


@pytest.mark.skip(
    reason="The cause if the error isn't clear: "
           "500 from CDEK"
)
def test_create_prealerts(cdek_client, delivery_request):
    send_orders = cdek_client.create_orders(delivery_request)

    assert send_orders
    assert len(send_orders) == 1
    order = send_orders[0]
    assert 'DispatchNumber' in order
    assert 'Number' in order

    dispatch_number = order['DispatchNumber']

    next_day = datetime.date.today() + datetime.timedelta(days=1)

    pre_alert_element = PreAlert(planned_meeting_date=next_day, pvz_code='XAB1')
    pre_alert_element.add_order(dispatch_number=dispatch_number)
    pre_alerts = cdek_client.create_prealerts(pre_alert_element)

    assert pre_alerts
    assert len(pre_alerts) == 1
    assert 'ErrorCode' in pre_alerts[0]
    # Проверить метод можно только на валидных данных авторизации
    assert pre_alerts[0]['ErrorCode'] == 'W_PA_17'
