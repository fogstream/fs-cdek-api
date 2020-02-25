# -*- coding: future_fstrings -*-
import datetime
import hashlib
import six
from typing import Dict, Union
from xml.etree import ElementTree
from xml.etree.ElementTree import tostring

from boltons.iterutils import remap


ARRAY_TAGS = {'State', 'Delay', 'Good', 'Fail', 'Item', 'Package'}


def xml_to_dict(xml):
    result = xml.attrib

    for child in xml:
        if child.tag in ARRAY_TAGS:
            result[child.tag] = result.get(child.tag, [])
            result[child.tag].append(xml_to_dict(child))
        else:
            result[child.tag] = xml_to_dict(child)

    return result


def xml_to_string(xml):
    tree = ElementTree.ElementTree(xml)

    for elem in tree.iter():
        elem.attrib = prepare_xml(elem.attrib)

    return tostring(tree.getroot(), encoding='UTF-8')


def clean_dict(data):
    """Очистка словаря от ключей со значением None.

    :param dict data: Словарь со значениями
    :return: Очищенный словарь
    :rtype: dict
    """
    return remap(data, lambda p, k, v: v is not None)


def prepare_xml(data):
    data = clean_dict(data)
    data = remap(data, lambda p, k, v: (k, six.text_type(v)))

    return data


def get_secure(secure_password,
               date):
    """Генерация секретного кода для запросов требующих авторизацию.

    :param str secure_password: Пароль для интеграции СДЭК
    :param date: дата документа
    :return: Секретный код
    :rtype: str
    """
    code = f'{date}&{secure_password}'.encode('utf-8')
    return hashlib.md5(code).hexdigest()
