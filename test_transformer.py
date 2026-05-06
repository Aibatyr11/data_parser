import unittest
from transformer import DataTransformer

class TestDataTransformer(unittest.TestCase):
    def setUp(self):
        self.date_list = ["122015", "122016"]
        self.period_names = ["Декабрь 2015", "Декабрь 2016"]
        self.raw_tree_mock = [
            {
                "id": "710000000",
                "text": "г.Астана",
                "parentId": "0",
                "y122015": "150.5",
                "y122016": "160.0",
                "leaf": "true"
            },
            {
                "id": "750000000",
                "text": "г.Алматы",
                "parentId": "0",
                "y122015": " ", # Пустое значение, должно обработаться корректно
                "y122016": "200.0",
                "leaf": "true"
            }
        ]

    def test_flatten_tree_data_mapping(self):
        """Проверка правильности разворачивания дерева JSON в плоский список"""
        result = DataTransformer.flatten_tree_data(
            self.raw_tree_mock, 
            self.date_list, 
            self.period_names
        )
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["kato_id"], "710000000")
        self.assertEqual(result[0]["period_code"], "122015")
        
    def test_aggregation_logic(self):
        """Проверка работы расчета экономических агрегатов"""
        base_value = 100.0
        result = DataTransformer.calculate_economic_aggregate(base_value)
        # Проверяем, что значение изменилось согласно логике (в нашем примере * 1.05)
        self.assertEqual(result, 105.0)

if __name__ == '__main__':
    unittest.main()
