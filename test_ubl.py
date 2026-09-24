# -*- coding: utf-8 -*-
"""Unit tests for GİB UBL-TR Invoice Viewer"""
import os
import unittest
from ubl_viewer import parse_ubl_invoice, generate_html_invoice, export_csv_items

class TestUBLViewer(unittest.TestCase):
    def setUp(self):
        self.sample_xml = os.path.join(os.path.dirname(__file__), "ornek_fatura.xml")

    def test_parse_invoice(self):
        data = parse_ubl_invoice(self.sample_xml)
        self.assertEqual(data["fatura_no"], "GIB2026000000042")
        self.assertEqual(data["fatura_tarihi"], "2026-09-24")
        self.assertEqual(data["para_birimi"], "TRY")
        self.assertEqual(data["satici"]["vkn_tckn"], "1234567890")
        self.assertEqual(data["alici"]["vkn_tckn"], "9876543210")
        self.assertEqual(data["tutarlar"]["odenecek_tutar"], 24000.0)
        self.assertEqual(len(data["kalemler"]), 1)
        self.assertEqual(data["kalemler"][0]["miktar"], 2.0)

    def test_generate_html(self):
        data = parse_ubl_invoice(self.sample_xml)
        out_html = os.path.join(os.path.dirname(__file__), "test_output.html")
        try:
            generate_html_invoice(data, out_html)
            self.assertTrue(os.path.exists(out_html))
            with open(out_html, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("GIB2026000000042", content)
            self.assertIn("Örnek Bilişim", content)
        finally:
            if os.path.exists(out_html):
                os.remove(out_html)

    def test_export_csv(self):
        data = parse_ubl_invoice(self.sample_xml)
        out_csv = os.path.join(os.path.dirname(__file__), "test_output.csv")
        try:
            export_csv_items(data, out_csv)
            self.assertTrue(os.path.exists(out_csv))
            with open(out_csv, "r", encoding="utf-8-sig") as f:
                content = f.read()
            self.assertIn("Bulut E-İmza", content)
            self.assertIn("20000.0", content)
        finally:
            if os.path.exists(out_csv):
                os.remove(out_csv)

if __name__ == "__main__":
    unittest.main()
