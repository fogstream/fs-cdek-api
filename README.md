CDEK-API
===========

[![Build Status](https://travis-ci.org/fogstream/fs-cdek-api.svg?branch=dev)](https://travis-ci.org/fogstream/fs-cdek-api)
[![Coverage Status](https://coveralls.io/repos/github/fogstream/fs-cdek-api/badge.svg?branch=dev)](https://coveralls.io/github/fogstream/fs-cdek-api?branch=dev)
[![PyPI Version](https://img.shields.io/pypi/v/fs-cdek-api.svg)](https://pypi.python.org/pypi/fs-cdek-api)


Описание
------------
Библиотека упрощающая работу с API службы доставки [СДЭК](https://www.cdek.ru/).

Установка
------------
Для работы требуется Python 3.6+
Для установки используйте [pipenv](http://pipenv.org/) (или pip):

```bash
$ pipenv install fs-cdek-api
$ pip install fs-cdek-api
```

Примеры
-------------

### Запрос доставки
```python
delivery_request = DeliveryRequest(number='12345678')
order = delivery_request.add_order(
    number=randint(100000, 1000000),
    recipient_name='Иванов Иван Иванович',
    phone='+79999999999',
    send_city_post_code='680000',
    rec_city_post_code='680000',
    seller_name='Магазин',
    comment='Товар',
    tariff_type_code=138,
    shipping_price=300.0,
)
delivery_request.add_address(order, pvz_code='XAB1')
package = delivery_request.add_package(
    order_element=order,
    size_a=10,
    size_b=10,
    size_c=10,
    number=randint(100000, 1000000),
    barcode=randint(100000, 1000000),
    weight=600,
)
delivery_request.add_item(
    package_element=package,
    weight=500,
    cost=1000,
    ware_key='12345678',
    comment='Товар',
)

cdek_client = CDEKClient('login', 'pass')
delivery_orders = cdek_client.create_orders(delivery_request)
```

### Удаление заказа
Условием возможности удаления заказа является отсутствие движения груза на 
складе СДЭК (статус заказа «Создан»).
```python
delete_requests = cdek_client.delete_orders(
    act_number=act_number,
    dispatch_numbers=[dispatch_number],
)
```

### Вызов курьера для забора груза ИМ
```python
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
```

### Информация о заказах
```python
dispatch_number = order['DispatchNumber']
info = cdek_client.get_orders_info([dispatch_number])
```

### Статусы заказов
```python
dispatch_number = order['DispatchNumber']
info = cdek_client.get_orders_statuses([dispatch_number])
```

### Печать накладной
Возврщает `pdf` документ в случае успеха.
```python
order_print = cdek_client.get_orders_print([dispatch_number])
```

### Печать ШК-мест
Возврщает `pdf` документ в случае успеха.
```python
barcode_print = cdek_client.get_barcode_print([dispatch_number])
```

### Список регионов
```python
regions = cdek_client.get_regions(region_code_ext=27)
```

### Список городов
```python
cities = cdek_client.get_cities(region_code_ext=27)
```

### Список ПВЗ
```python
pvz_list = cdek_client.get_delivery_points(city_post_code=680000)['pvz']
```

### Расчет стоимости доставки
```python
shipping_costs = cdek_client.get_shipping_cost(
    sender_city_id=270,
    receiver_city_id=44,
    goods=[
        {'weight': 0.3, 'length': 10, 'width': 7, 'height': 5},
        {'weight': 0.1, 'volume': 0.1},
    ],
    tariff_id=3,
)
```

### Создание преалерта
```python
next_day = datetime.date.today() + datetime.timedelta(days=1)

pre_alert_element = PreAlert(planned_meeting_date=next_day, pvz_code='XAB1')
pre_alert_element.add_order(dispatch_number=dispatch_number)
pre_alerts = cdek_client.create_prealerts(pre_alert_element)
```