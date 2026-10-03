import logging
import tempfile
import unittest
from pathlib import Path

from app_logging import configure_app_logging


class ApplicationLoggingTests(unittest.TestCase):
    def test_logs_timestamp_level_and_readable_error_to_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / 'app.log'
            logger = configure_app_logging(log_path)
            try:
                try:
                    raise ValueError('Проверьте входные параметры.')
                except ValueError:
                    logger.exception('Ошибка тестового расчета')

                for handler in logger.handlers:
                    handler.flush()

                content = log_path.read_text(encoding='utf-8')
            finally:
                for handler in list(logger.handlers):
                    logger.removeHandler(handler)
                    handler.close()

        self.assertIn('ERROR', content)
        self.assertIn('Ошибка тестового расчета', content)
        self.assertIn('Проверьте входные параметры.', content)
        self.assertRegex(content, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')


if __name__ == '__main__':
    unittest.main()
