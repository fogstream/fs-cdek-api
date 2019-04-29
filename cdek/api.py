import datetime
import json
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import requests

from cdek.entities import CallCourier, DeliveryRequest, PreAlert
from cdek.utils import clean_dict, get_secure, xml_to_dict, xml_to_string


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

    def __init__(self, account: str, secure_password: str,
                 api_url: str = 'http://integration.cdek.ru',
                 test: bool = False):
        self._account = account
        self._secure_password = secure_password
        self._api_url = api_url
        self._test = test

    def _exec_request(self, url: str, data: Dict, method: str = 'GET',
                      stream: bool = False) -> requests.Response:
        if isinstance(data, dict):
            data = clean_dict(data)

        url = self._api_url + url

        if method == 'GET':
            response = requests.get(f'{url}?{urlencode(data)}', stream=stream)
        elif method == 'POST':
            response = requests.post(url, data=data, stream=stream)
        else:
            raise NotImplementedError(f'Unknown method "{method}"')

        return response

    def _exec_xml_request(self, url: str, xml_element: Element,
                          parse: bool = True) -> ElementTree:
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
            response = ElementTree.fromstring(response.text)

        return response

    def get_shipping_cost(
            self, sender_city_id: int, receiver_city_id: int,
            goods: List[Dict],
            sender_city_post_code: Optional[str] = None,
            receiver_city_post_code: Optional[str] = None,
            tariff_id: Optional[int] = None,
            tariffs: Optional[List[int]] = None,
    ) -> Dict:
        """
        Возвращает информацию о стоимости и сроках доставки
        Для отправителя и получателя обязателен один из параметров:
        *_city_id или *_city_postcode внутри *_city_data
        :param receiver_city_post_code:
        :param sender_city_post_code:
        :param tariff_id:
        :param sender_city_id: ID города отправителя по базе СДЭК
        :param receiver_city_id: ID города получателя по базе СДЭК
        :param tariffs: список тарифов
        :param goods: список товаров
        :return стоимость доставки
        :rtype: dict
        """

        today = datetime.date.today().isoformat()

        params = {
            'version': '1.0',
            'dateExecute': today,
            'senderCityId': sender_city_id,
            'receiverCityId': receiver_city_id,
            'senderCityPostCode': sender_city_post_code,
            'receiverCityPostCode': receiver_city_post_code,
            'goods': goods,
        }

        if not self._test:
            params['authLogin'] = self._account
            params['secure'] = get_secure(self._secure_password, today)

        if tariff_id:
            params['tariffId'] = tariff_id
        elif tariffs:
            tariff_list = [
                {'priority': -i, 'id': tariff}
                for i, tariff in enumerate(tariffs, 1)
            ]
            params['tariffList'] = tariff_list
        else:
            raise AttributeError('Tariff required')

        response = requests.post(
            self.CALCULATOR_URL,
            data=json.dumps(params),
        ).json()

        return response

    def get_delivery_points(
            self, city_post_code: Optional[Union[int, str]] = None,
            city_id: Optional[Union[str, int]] = None,
            point_type: str = 'PVZ',
            have_cash_less: Optional[bool] = None,
            allowed_cod: Optional[bool] = None) -> Dict[str, List]:
        """
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
        ).json()

        return response

    def get_regions(self, region_code_ext: Optional[int] = None,
                    region_code: Optional[int] = None,
                    page: int = 0, size: int = 1000) -> List[Dict]:
        """
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
                'countryCode': 'RU',
                'page': page,
                'size': size,
            },
        ).json()

        return response

    def get_cities(self, region_code_ext: Optional[int] = None,
                   region_code: Optional[int] = None,
                   page: int = 0, size: int = 1000) -> List[Dict]:
        """
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
                'countryCode': 'RU',
                'page': page,
                'size': size,
            },
        ).json()

        return response

    def create_orders(self, delivery_request: DeliveryRequest):
        """
        Создать заказ
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
            self, act_number: str, dispatch_numbers: List[str]) -> List[Dict]:
        """
        Удалить заказ
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

    def call_courier(self, call_courier: CallCourier) -> Dict:
        """
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

    def create_prealerts(self, pre_alert: PreAlert):
        """
        Метод для создания сводного реестра (преалерта), содержащего
        все накладные, товары по которым передаются в СДЭК на доставку.
        :return: Результат создания преалерта
        """
        xml = self._exec_xml_request(
            self.PREALERT_URL,
            xml_element=pre_alert.to_xml(),
        )

        return [xml_to_dict(order) for order in xml.findall('Order')]

    def get_orders_info(self, orders_dispatch_numbers: List[int]) -> List[Dict]:
        """
        Информация по заказам
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

    def get_orders_statuses(self, orders_dispatch_numbers: List[int],
                            show_history: bool = True) -> List[Dict]:
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

    def get_orders_print(self, orders_dispatch_numbers: List[int],
                         copy_count: int = 1) -> Optional[requests.Response]:
        """
        Печатная форма квитанции к заказу
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

    def get_barcode_print(self, orders_dispatch_numbers: List[int],
                          copy_count: int = 1) -> Optional[requests.Response]:
        """
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
