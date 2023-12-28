# -*- coding: future_fstrings -*-
import datetime
import json
from typing import Dict, List, Optional, Union
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import requests

from .entities import CallCourier, DeliveryRequest, PreAlert
from .utils import clean_dict, get_secure, xml_to_dict, xml_to_string


class CDEKClient:
    # Калькулятор стоимости доставки
    CALCULATOR_URL = 'http://api.cdek.ru/calculator/calculate_price_by_json.php'
    # Список регионов
    REGIONS_URL = '/v1/location/regions/json'
    # Список городов
    CITIES_URL = '/v1/location/cities/json'
    # Создание заказа
    CREATE_ORDER_URL = '/new_orders.php'
    # Удаление заказа
    DELETE_ORDER_URL = '/delete_orders.php'
    # Создание преалерта
    PREALERT_URL = '/addPreAlert'
    # Статус заказа
    ORDER_STATUS_URL = '/status_report_h.php'
    # Печать ШК-мест
    BARCODE_PRINT_URL = '/ordersPackagesPrint'
    # Информация о заказе
    ORDER_INFO_URL = '/info_report.php'
    # Печать квитанции к заказу
    ORDER_PRINT_URL = '/orders_print.php'
    # Точки выдачи
    DELIVERY_POINTS_URL = '/pvzlist/v1/json'
    # Вызов курьера
    CALL_COURIER_URL = '/call_courier.php'
    # Таймаут запроса стоимости
    SHIPPING_COST_TIMEOUT = 3

    def __init__(self, account, secure_password,
                 api_url = 'http://integration.cdek.ru',
                 test = False):
        self._account = account
        self._secure_password = secure_password
        self._api_url = api_url
        self._test = test

    def _exec_request(self, url, data, method = 'GET',
                      stream = False, **kwargs):
        if isinstance(data, dict):
            data = clean_dict(data)

        url = self._api_url + url

        if method == 'GET':
            response = requests.get(
                f'{url}?{urlencode(data)}', stream=stream, **kwargs
            )
        elif method == 'POST':
            response = requests.post(url, data=data, stream=stream, **kwargs)
        else:
            raise NotImplementedError(f'Unknown method "{method}"')

        response.raise_for_status()

        return response

    def _exec_xml_request(self, url, xml_element,
                          parse = True):
        now = datetime.date.today().isoformat()
        xml_element.attrib['Date'] = now
        xml_element.attrib['Account'] = self._account
        xml_element.attrib['Secure'] = get_secure(self._secure_password, now)

        response = self._exec_request(
            url=url,
            data={'xml_request': xml_to_string(xml_element)},
            method='POST',
        )
        if parse:
            response = ElementTree.fromstring(response.content)

        return response

    def get_shipping_cost(
            self,
            goods,
            sender_city_id = None,
            receiver_city_id = None,
            sender_city_post_code = None,
            receiver_city_post_code = None,
            tariff_id = None,
            tariffs = None,
            services = None,
            date_execute = None,
    ):
        """Расчет стоимости и сроков доставки.

        Для отправителя и получателя обязателен один из параметров:
        *_city_id или *_city_postcode внутри *_city_data

        :param receiver_city_post_code: Почтовый индекс города получателя
        :param sender_city_post_code: Почтовый индекс города отправителя
        :param tariff_id: ID тарифа
        :param sender_city_id: ID города отправителя по базе СДЭК
        :param receiver_city_id: ID города получателя по базе СДЭК
        :param tariffs: список тарифов
        :param goods: список товаров
        :param services: список дополнительных услуг
        :param date_execute: планируемая дата отправки заказа
        :return: стоимость доставки
        :rtype: dict
        """
        if date_execute is None:
            date_execute = datetime.date.today()
        date_in_isoformat = date_execute.isoformat()

        params = {
            'version': '1.0',
            'dateExecute': date_in_isoformat,
            'senderCityId': sender_city_id,
            'receiverCityId': receiver_city_id,
            'senderCityPostCode': sender_city_post_code,
            'receiverCityPostCode': receiver_city_post_code,
            'goods': goods,
            'services': services,
        }

        if not self._test:
            params['authLogin'] = self._account
            params['secure'] = get_secure(self._secure_password, date_in_isoformat)

        if tariff_id:
            params['tariffId'] = tariff_id
        elif tariffs:
            tariff_list = [
                {'priority': i, 'id': tariff}
                for i, tariff in enumerate(tariffs, 1)
            ]
            params['tariffList'] = tariff_list
        else:
            raise AttributeError('Tariff required')

        response = requests.post(
            self.CALCULATOR_URL,
            data=json.dumps(params),
            headers={'Content-Type': 'application/json'},
            timeout=self.SHIPPING_COST_TIMEOUT,
        )
        response.raise_for_status()

        return response.json()

    def get_delivery_points(
            self, city_post_code = None,
            city_id = None,
            point_type = 'PVZ',
            have_cash_less = None,
            allowed_cod = None):
        """Список ПВЗ.

        Возвращает списков пунктов самовывоза для указанного города,
        либо для всех если город не указан

        :param str city_post_code: Почтовый индекс города
        :param str city_id: Код города по базе СДЭК
        :param str point_type: Тип пункта выдачи ['PVZ', 'POSTOMAT', 'ALL']
        :param bool have_cash_less: Наличие терминала оплаты
        :param bool allowed_cod: Разрешен наложенный платеж
        :return: Список точек выдачи
        :rtype: list
        """
        response = self._exec_request(
            url=self.DELIVERY_POINTS_URL,
            data={
                'citypostcode': city_post_code,
                'cityid': city_id,
                'type': point_type,
                'havecashless': have_cash_less,
                'allowedcode': allowed_cod,
            },
            timeout=60,
        ).json()

        return response

    def get_regions(self, region_code_ext = None,
                    region_code = None,
                    country_code = 'RU',
                    page = 0, size = 1000):
        """Список регионов.

        Метод используется для получения детальной информации о регионах.

        :param region_code_ext: Код региона
        :param region_code:	Код региона в ИС СДЭК
        :param int page: Номер страницы выборки
        :param int size: Ограничение выборки
        :return: Список регионов по заданным параметрам
        :rtype: list
        """
        response = self._exec_request(
            url=self.REGIONS_URL,
            data={
                'regionCodeExt': region_code_ext,
                'regionCode': region_code,
                'countryCode': country_code,
                'page': page,
                'size': size,
            },
            timeout=60,
        ).json()

        return response

    def get_cities(self, region_code_ext = None,
                   region_code = None,
                   country_code = 'RU',
                   page = 0, size = 1000):
        """Список городов.

        Метод используется для получения детальной информации о городах.

        :param region_code_ext: Код региона
        :param region_code: Код региона в ИС СДЭК
        :param page: Номер страницы выборки
        :param size: Ограничение выборки
        :return: Список городов по заданным параметрам
        :rtype: list
        """
        response = self._exec_request(
            url=self.CITIES_URL,
            data={
                'regionCodeExt': region_code_ext,
                'regionCode': region_code,
                'countryCode': country_code,
                'page': page,
                'size': size,
            },
            timeout=60,
        ).json()

        return response

    def create_orders(self, delivery_request):
        """Создание заказа.

        :param DeliveryRequest delivery_request: Запрос доставки
        :return: Информация о созданном заказе
        :rtype: dict
        """
        xml = self._exec_xml_request(
            url=self.CREATE_ORDER_URL,
            xml_element=delivery_request.to_xml(),
        )

        return [xml_to_dict(order) for order in
                xml.findall('*[@DispatchNumber]')]

    def delete_orders(
            self, act_number, dispatch_numbers):
        """Удаление заказа.

        :param str act_number: Номера акта приема-передачи.
            Идентификатор заказа в ИС клиента СДЭК.
        :param list dispatch_numbers: Номера заказов СДЭК
        :return: Удаленные заказы
        :rtype: dict
        """
        delete_request_element = ElementTree.Element(
            'DeleteRequest',
            Number=act_number,
            OrderCount=1,
        )

        for dispatch_number in dispatch_numbers:
            ElementTree.SubElement(
                delete_request_element,
                'Order',
                DispatchNumber=dispatch_number,
            )

        xml = self._exec_xml_request(
            url=self.DELETE_ORDER_URL,
            xml_element=delete_request_element,
        )

        return [xml_to_dict(order) for order in
                xml.findall('*[@DispatchNumber]')]

    def call_courier(self, call_courier):
        """Вызов курьера.

        Вызов курьера для забора посылки у ИМ

        :param CallCourier call_courier: Запрос вызова
        :return: Объект вызова
        :rtype: dict
        """
        xml = self._exec_xml_request(
            url=self.CALL_COURIER_URL,
            xml_element=call_courier.to_xml(),
        )

        return xml_to_dict(xml.find('Call'))

    def create_prealerts(self, pre_alert):
        """Создание преалерта.

        Метод для создания сводного реестра (преалерта), содержащего
        все накладные, товары по которым передаются в СДЭК на доставку.

        :return: Результат создания преалерта
        """
        xml = self._exec_xml_request(
            self.PREALERT_URL,
            xml_element=pre_alert.to_xml(),
        )

        return [xml_to_dict(order) for order in xml.findall('Order')]

    def get_orders_info(self, orders_dispatch_numbers):
        """Информация по заказам.

        :param orders_dispatch_numbers: список номеров отправлений СДЭК
        :returns list
        """
        info_request = ElementTree.Element('InfoRequest')
        for dispatch_number in orders_dispatch_numbers:
            ElementTree.SubElement(
                info_request,
                'Order',
                DispatchNumber=dispatch_number,
            )

        xml = self._exec_xml_request(self.ORDER_INFO_URL, info_request)

        return [xml_to_dict(order) for order in xml.findall('Order')]

    def get_orders_statuses(
            self,
            orders_dispatch_numbers,
            show_history = True
    ):
        """
        Статусы заказов
        :param orders_dispatch_numbers: список номеров отправлений СДЭК
        :param show_history: получать историю статусов
        :returns list
        """
        status_report_element = ElementTree.Element(
            'StatusReport',
            ShowHistory=show_history,
        )

        for dispatch_number in orders_dispatch_numbers:
            ElementTree.SubElement(
                status_report_element,
                'Order',
                DispatchNumber=dispatch_number,
            )

        xml = self._exec_xml_request(
            url=self.ORDER_STATUS_URL,
            xml_element=status_report_element,
        )

        return [xml_to_dict(order) for order in xml.findall('Order')]

    def get_orders_print(
            self,
            orders_dispatch_numbers,
            copy_count = 1
    ):
        """Печатная форма квитанции к заказу.

        :param orders_dispatch_numbers: Список номеров отправлений СДЭК
        :param copy_count: Количество копий
        """
        orders_print_element = ElementTree.Element(
            'OrdersPrint',
            OrderCount=len(orders_dispatch_numbers),
            CopyCount=copy_count,
        )

        for dispatch_number in orders_dispatch_numbers:
            ElementTree.SubElement(
                orders_print_element,
                'Order',
                DispatchNumber=dispatch_number,
            )

        response = self._exec_xml_request(
            url=self.ORDER_PRINT_URL,
            xml_element=orders_print_element,
            parse=False,
        )

        return response if not response.content.startswith(b'<?xml') else None

    def get_barcode_print(
            self,
            orders_dispatch_numbers,
            copy_count = 1
    ):
        """Печать этикетки.

        Метод используется для формирования печатной формы
        этикетки для упаковки в формате pdf.

        :param list orders_dispatch_numbers: Список номеров отправлений СДЭК
        :param int copy_count: Количество копий
        """
        orders_packages_print_element = ElementTree.Element(
            'OrdersPackagesPrint',
            OrderCount=len(orders_dispatch_numbers),
            CopyCount=copy_count,
        )

        for dispatch_number in orders_dispatch_numbers:
            ElementTree.SubElement(
                orders_packages_print_element,
                'Order',
                DispatchNumber=dispatch_number,
            )

        response = self._exec_xml_request(
            url=self.BARCODE_PRINT_URL,
            xml_element=orders_packages_print_element,
            parse=False,
        )

        return response if not response.content.startswith(b'<?xml') else None
