# -*- coding: utf-8 -*-
"""Unit tests for GİB UBL-TR Invoice, Despatch, e-SMM & e-MM Viewer v1.3"""
import os
import unittest
from ubl_viewer import parse_ubl_document, generate_html_invoice, export_csv_items

class TestUBLViewer(unittest.TestCase):
    def setUp(self):
        self.sample_xml = os.path.join(os.path.dirname(__file__), "ornek_fatura.xml")

    def test_parse_invoice(self):
        data = parse_ubl_document(self.sample_xml)
        self.assertEqual(data["fatura_no"], "GIB2026000000042")
        self.assertEqual(data["fatura_tarihi"], "2026-09-24")
        self.assertEqual(data["para_birimi"], "TRY")
        self.assertEqual(data["satici"]["vkn_tckn"], "1234567890")
        self.assertEqual(data["alici"]["vkn_tckn"], "9876543210")
        self.assertEqual(data["tutarlar"]["odenecek_tutar"], 24000.0)
        self.assertEqual(len(data["kalemler"]), 1)
        self.assertEqual(data["kalemler"][0]["miktar"], 2.0)

    def test_simulated_despatch(self):
        temp_despatch = os.path.join(os.path.dirname(__file__), "temp_despatch.xml")
        try:
            with open(temp_despatch, "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="UTF-8"?>
<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2">
    <ID>IRS2026000000100</ID>
    <IssueDate>2026-09-25</IssueDate>
    <DespatchSupplierParty>
        <Party>
            <PartyName><Name>Lojistik A.Ş.</Name></PartyName>
            <PartyIdentification><ID schemeID="VKN">5555555555</ID></PartyIdentification>
        </Party>
    </DespatchSupplierParty>
    <CarrierParty>
        <PartyName><Name>Hızlı Kargo Ltd.</Name></PartyName>
        <LicensePlateID>34 AB 1234</LicensePlateID>
    </CarrierParty>
    <DespatchLine>
        <ItemDescription>Sanayi Tipi Motor</ItemDescription>
        <DeliveredQuantity>5</DeliveredQuantity>
    </DespatchLine>
</DespatchAdvice>""")
            data = parse_ubl_document(temp_despatch)
            self.assertEqual(data["belge_turu"], "e-İrsaliye")
            self.assertEqual(data["fatura_no"], "IRS2026000000100")
            self.assertEqual(data["tasiyici"]["unvan"], "Hızlı Kargo Ltd.")
            self.assertEqual(data["tasiyici"]["plaka"], "34 AB 1234")
            self.assertEqual(len(data["kalemler"]), 1)
            self.assertEqual(data["kalemler"][0]["urun"], "Sanayi Tipi Motor")
            self.assertEqual(data["kalemler"][0]["miktar"], 5.0)
        finally:
            if os.path.exists(temp_despatch):
                os.remove(temp_despatch)

    def test_generate_html(self):
        data = parse_ubl_document(self.sample_xml)
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
        data = parse_ubl_document(self.sample_xml)
        out_csv = os.path.join(os.path.dirname(__file__), "test_output.csv")
        try:
            export_csv_items(data, out_csv)
            self.assertTrue(os.path.exists(out_csv))
            with open(out_csv, "r", encoding="utf-8-sig") as f:
                content = f.read()
            self.assertIn("Bulut E-İmza", content)
            self.assertIn("20000", content)
        finally:
            if os.path.exists(out_csv):
                os.remove(out_csv)

    def test_foreign_plate_and_investment_incentive(self):
        temp_xml = os.path.join(os.path.dirname(__file__), "temp_foreign.xml")
        try:
            with open(temp_xml, "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="UTF-8"?>
<DespatchAdvice xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2">
    <ID>IRS2026000000999</ID>
    <IssueDate>2026-10-20</IssueDate>
    <YatirimTesvikTaxExemptionReasonCode>324</YatirimTesvikTaxExemptionReasonCode>
    <CarrierParty>
        <PartyName><Name>Global Nakliyat</Name></PartyName>
        <LicensePlateID schemeID="YABANCIPLAKA">B 1234 XY</LicensePlateID>
        <LicensePlateID schemeID="YABANCIDORSE">BG 9988 AA</LicensePlateID>
    </CarrierParty>
    <DespatchLine>
        <ItemDescription>Teşvik Kapsamı CNC Tezgah</ItemDescription>
        <DeliveredQuantity>1</DeliveredQuantity>
    </DespatchLine>
</DespatchAdvice>""")
            data = parse_ubl_document(temp_xml)
            self.assertEqual(data["tasiyici"]["plaka"], "B 1234 XY")
            self.assertEqual(data["tasiyici"]["dorse_plaka"], "BG 9988 AA")
            self.assertIn(data["tasiyici"]["plaka_tipi"], ["YABANCIPLAKA", "YABANCIDORSE"])
            self.assertIn("324", data["istisna_kodlari"])
        finally:
            if os.path.exists(temp_xml):
                os.remove(temp_xml)

    def test_xades_bes_signature_parsing(self):
        temp_sig_xml = os.path.join(os.path.dirname(__file__), "temp_xades.xml")
        try:
            with open(temp_sig_xml, "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
         xmlns:xades="http://uri.etsi.org/01903/v1.3.2#">
    <ID>GIB2026000000888</ID>
    <IssueDate>2026-10-23</IssueDate>
    <InvoiceTypeCode>SATIS</InvoiceTypeCode>
    <ds:Signature Id="Signature_1">
        <ds:SignedInfo>
            <ds:Reference URI="">
                <ds:DigestValue>mK2+bO7xM8k=</ds:DigestValue>
            </ds:Reference>
        </ds:SignedInfo>
        <ds:KeyInfo>
            <ds:X509Data>
                <ds:X509SubjectName>serialNumber=1234567890, CN=Test Mali Mühür Ltd.</ds:X509SubjectName>
                <ds:X509IssuerName>CN=TÜBİTAK BİLGEM Kamu SM, O=TÜBİTAK</ds:X509IssuerName>
                <ds:X509SerialNumber>9988776655</ds:X509SerialNumber>
            </ds:X509Data>
        </ds:KeyInfo>
        <ds:Object>
            <xades:QualifyingProperties>
                <xades:SignedProperties>
                    <xades:SignedSignatureProperties>
                        <xades:SigningTime>2026-10-23T10:15:00Z</xades:SigningTime>
                    </xades:SignedSignatureProperties>
                </xades:SignedProperties>
            </xades:QualifyingProperties>
        </ds:Object>
    </ds:Signature>
</Invoice>""")
            data = parse_ubl_document(temp_sig_xml)
            sig = data["imza_bilgileri"]
            self.assertTrue(sig["imzali_mi"])
            self.assertEqual(sig["eshs_saglayici"], "Kamu SM")
            self.assertEqual(sig["imzaci_vkn"], "1234567890")
            self.assertEqual(sig["digest_value"], "mK2+bO7xM8k=")
            self.assertEqual(sig["sertifika_seri_no"], "9988776655")
            self.assertIn("2026-10-23", sig["imza_zamani"])
        finally:
            if os.path.exists(temp_sig_xml):
                os.remove(temp_sig_xml)

    def test_e_smm_and_mustahsil_support(self):
        # e-SMM Test
        temp_smm = os.path.join(os.path.dirname(__file__), "temp_smm.xml")
        try:
            with open(temp_smm, "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <ID>SMM2026000000015</ID>
    <IssueDate>2026-10-22</IssueDate>
    <InvoiceTypeCode>SERBESTMESLEKMAKBUZU</InvoiceTypeCode>
    <LegalMonetaryTotal>
        <LineExtensionAmount>10000.00</LineExtensionAmount>
        <PayableAmount>10000.00</PayableAmount>
    </LegalMonetaryTotal>
    <TaxTotal>
        <TaxAmount>2000.00</TaxAmount>
        <TaxSubtotal>
            <TaxAmount>2000.00</TaxAmount>
            <Percent>20.0</Percent>
        </TaxSubtotal>
    </TaxTotal>
    <InvoiceLine>
        <ItemDescription>Hukuki Danışmanlık Hizmeti</ItemDescription>
        <LineExtensionAmount>10000.00</LineExtensionAmount>
    </InvoiceLine>
</Invoice>""")
            smm_data = parse_ubl_document(temp_smm)
            self.assertIn("e-Serbest Meslek Makbuzu", smm_data["belge_turu"])
            self.assertEqual(smm_data["tutarlar"]["mal_hizmet_toplam"], 10000.0)
            self.assertEqual(smm_data["tutarlar"]["stopaj_toplam"], 2000.0)
            self.assertEqual(smm_data["tutarlar"]["net_tutar"], 10000.0)
        finally:
            if os.path.exists(temp_smm):
                os.remove(temp_smm)

        # e-MM Test
        temp_mm = os.path.join(os.path.dirname(__file__), "temp_mm.xml")
        try:
            with open(temp_mm, "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <ID>GIB2026000000077</ID>
    <IssueDate>2026-10-22</IssueDate>
    <InvoiceTypeCode>MUSTAHSILMAKBUZ</InvoiceTypeCode>
    <LegalMonetaryTotal>
        <LineExtensionAmount>50000.00</LineExtensionAmount>
        <PayableAmount>48000.00</PayableAmount>
    </LegalMonetaryTotal>
    <Note>GV Stopajı: 1000.00 TL | Ticaret Borsası Kesintisi: 1000.00 TL</Note>
</Invoice>""")
            mm_data = parse_ubl_document(temp_mm)
            self.assertIn("e-Müstahsil Makbuzu", mm_data["belge_turu"])
            self.assertEqual(mm_data["fatura_no"], "GIB2026000000077")
        finally:
            if os.path.exists(temp_mm):
                os.remove(temp_mm)

    def test_ev_charging_energy_invoice(self):
        temp_ev = os.path.join(os.path.dirname(__file__), "temp_ev.xml")
        try:
            with open(temp_ev, "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
    <ID>EVF2026000000555</ID>
    <IssueDate>2026-10-23</IssueDate>
    <Note>Şarj Ağı İstasyon ID: TR-IST-LEVENT-01 | Soket ID: CCS-DC-180KW-02 | EPDK Lisans: SARJ/001</Note>
    <InvoiceLine>
        <ItemDescription>Elektrikli Araç DC Hızlı Şarj Hizmeti</ItemDescription>
        <InvoicedQuantity unitCode="KWH">45.5</InvoicedQuantity>
        <PriceAmount>8.50</PriceAmount>
        <LineExtensionAmount>386.75</LineExtensionAmount>
    </InvoiceLine>
</Invoice>""")
            ev_data = parse_ubl_document(temp_ev)
            es = ev_data["enerji_sarj_bilgileri"]
            self.assertTrue(es["enerji_faturasi_mi"])
            self.assertEqual(es["tuketim_kwh"], 45.5)
            self.assertEqual(es["kwh_birim_fiyat"], 8.50)
            self.assertEqual(es["istasyon_id"], "TR-IST-LEVENT-01")
            self.assertEqual(es["soket_id"], "CCS-DC-180KW-02")
            self.assertEqual(es["epdk_lisans"], "SARJ/001")
        finally:
            if os.path.exists(temp_ev):
                os.remove(temp_ev)

if __name__ == "__main__":
    unittest.main()
