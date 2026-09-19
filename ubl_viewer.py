#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GİB UBL-TR e-Fatura & e-Arşiv XML Görüntüleyici ve Bilgi Okuyucu
==============================================================
Bu betik, Gelir İdaresi Başkanlığı UBL-TR 1.2 standardındaki e-Fatura ve e-Arşiv
XML dosyalarını ayrıştırarak; fatura kalemlerini, satıcı/alıcı bilgilerini,
KDV ve ödenecek tutarları terminalde gösterir veya modern bir HTML faturası üretir.

Yazar: E-İmza & Dijital Dönüşüm Portalı (https://efatura-atolyesi.pages.dev/yazilar/e-fatura-ve-e-arsiv-arasindaki-farklar.html)
Lisans: MIT
"""

import sys
import os
import re
import json
import webbrowser
import argparse
import xml.etree.ElementTree as ET

def clean_tag(tag):
    """XML etiketindeki isim alanını (namespace) temizler."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def parse_ubl_invoice(xml_path):
    """UBL-TR e-Fatura XML dosyasını ayrıştırır."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # İsim alanlarını yok sayarak arama yapmak için yardımcı sözlük
    data = {
        "fatura_no": "",
        "fatura_tarihi": "",
        "fatura_tipi": "SATIS",
        "para_birimi": "TRY",
        "satici": { "unvan": "", "vkn_tckn": "", "vergi_dairesi": "", "sehir": "" },
        "alici":  { "unvan": "", "vkn_tckn": "", "vergi_dairesi": "", "sehir": "" },
        "tutarlar": { "mal_hizmet_toplam": 0.0, "kdv_toplam": 0.0, "odenecek_tutar": 0.0 },
        "kalemler": []
    }

    # XPath / iterasyon ile ana alanları tara
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "").strip()

        if tag == "ID" and not data["fatura_no"]:
            data["fatura_no"] = val
        elif tag == "IssueDate" and not data["fatura_tarihi"]:
            data["fatura_tarihi"] = val
        elif tag == "InvoiceTypeCode" and not data["fatura_tipi"]:
            data["fatura_tipi"] = val
        elif tag == "DocumentCurrencyCode" and not data["para_birimi"]:
            data["para_birimi"] = val

    # Satıcı (AccountingSupplierParty)
    for party in root.iter():
        if clean_tag(party.tag) == "AccountingSupplierParty":
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not data["satici"]["unvan"]:
                    data["satici"]["unvan"] = cval
                elif ctag == "ID" and not data["satici"]["vkn_tckn"]:
                    data["satici"]["vkn_tckn"] = cval
                elif ctag == "CityName":
                    data["satici"]["sehir"] = cval

    # Alıcı (AccountingCustomerParty)
    for party in root.iter():
        if clean_tag(party.tag) == "AccountingCustomerParty":
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not data["alici"]["unvan"]:
                    data["alici"]["unvan"] = cval
                elif ctag == "ID" and not data["alici"]["vkn_tckn"]:
                    data["alici"]["vkn_tckn"] = cval
                elif ctag == "CityName":
                    data["alici"]["sehir"] = cval

    # Tutarlar
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        try:
            val_float = float((elem.text or "0").replace(",", "."))
            if tag == "LineExtensionAmount" and data["tutarlar"]["mal_hizmet_toplam"] == 0:
                data["tutarlar"]["mal_hizmet_toplam"] = val_float
            elif tag == "TaxAmount" and data["tutarlar"]["kdv_toplam"] == 0:
                data["tutarlar"]["kdv_toplam"] = val_float
            elif tag == "PayableAmount" and data["tutarlar"]["odenecek_tutar"] == 0:
                data["tutarlar"]["odenecek_tutar"] = val_float
        except ValueError:
            pass

    # Kalemler (InvoiceLine)
    for line in root.iter():
        if clean_tag(line.tag) == "InvoiceLine":
            item_name = ""
            qty = 1.0
            price = 0.0
            total = 0.0
            for c in line.iter():
                ctag = clean_tag(c.tag)
                cval = (c.text or "").strip()
                if ctag in ["Name", "ItemDescription"]:
                    item_name = cval
                elif ctag == "InvoicedQuantity":
                    try: qty = float(cval)
                    except: pass
                elif ctag == "PriceAmount":
                    try: price = float(cval)
                    except: pass
                elif ctag == "LineExtensionAmount":
                    try: total = float(cval)
                    except: pass
            if item_name:
                data["kalemler"].append({
                    "urun": item_name,
                    "miktar": qty,
                    "fiyat": price,
                    "toplam": total
                })

    return data

def generate_html_invoice(data, output_path):
    """UBL verisinden modern bir HTML faturası üretir."""
    kalemler_tr = ""
    for idx, k in enumerate(data["kalemler"]):
        kalemler_tr += f"""
        <tr class="border-b border-slate-100 text-sm">
            <td class="py-2.5 px-3 text-slate-500">{idx+1}</td>
            <td class="py-2.5 px-3 font-medium text-slate-800">{k['urun']}</td>
            <td class="py-2.5 px-3 text-right">{k['miktar']}</td>
            <td class="py-2.5 px-3 text-right">{k['fiyat']:,.2f} {data['para_birimi']}</td>
            <td class="py-2.5 px-3 text-right font-semibold text-slate-900">{k['toplam']:,.2f} {data['para_birimi']}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>e-Fatura: {data['fatura_no']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 text-slate-800 p-4 sm:p-8">
    <div class="max-w-3xl mx-auto bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <div class="flex justify-between items-start border-b border-slate-200 pb-6">
            <div>
                <span class="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                    e-Fatura ({data['fatura_tipi']})
                </span>
                <h1 class="text-2xl font-black text-slate-900 mt-2">{data['fatura_no']}</h1>
                <p class="text-xs text-slate-500 mt-0.5">Düzenleme Tarihi: {data['fatura_tarihi']}</p>
            </div>
            <div class="text-right">
                <span class="text-xs text-slate-400 font-bold block">ÖDENECEK TUTAR</span>
                <span class="text-3xl font-extrabold text-emerald-600">{data['tutarlar']['odenecek_tutar']:,.2f} {data['para_birimi']}</span>
            </div>
        </div>

        <div class="grid grid-cols-2 gap-8 my-6 text-sm">
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">SATICI BİLGİLERİ</span>
                <p class="font-bold text-slate-900">{data['satici']['unvan'] or 'Belirtilmemiş'}</p>
                <p class="text-xs text-slate-600 mt-1">VKN/TCKN: <span class="font-mono">{data['satici']['vkn_tckn']}</span></p>
                <p class="text-xs text-slate-500">{data['satici']['sehir']}</p>
            </div>
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">ALICI BİLGİLERİ</span>
                <p class="font-bold text-slate-900">{data['alici']['unvan'] or 'Belirtilmemiş'}</p>
                <p class="text-xs text-slate-600 mt-1">VKN/TCKN: <span class="font-mono">{data['alici']['vkn_tckn']}</span></p>
                <p class="text-xs text-slate-500">{data['alici']['sehir']}</p>
            </div>
        </div>

        <table class="w-full text-left border-collapse my-6">
            <thead>
                <tr class="border-b border-slate-200 text-xs text-slate-400 uppercase tracking-wider">
                    <th class="py-2 px-3">#</th>
                    <th class="py-2 px-3">Mal / Hizmet</th>
                    <th class="py-2 px-3 text-right">Miktar</th>
                    <th class="py-2 px-3 text-right">Birim Fiyat</th>
                    <th class="py-2 px-3 text-right">Toplam</th>
                </tr>
            </thead>
            <tbody>
                {kalemler_tr or '<tr><td colspan="5" class="py-4 text-center text-slate-400 text-sm">Detay kalem bulunamadı.</td></tr>'}
            </tbody>
        </table>

        <div class="border-t border-slate-200 pt-4 flex justify-end">
            <div class="w-64 space-y-1.5 text-sm">
                <div class="flex justify-between text-slate-600">
                    <span>Mal/Hizmet Toplamı:</span>
                    <span>{data['tutarlar']['mal_hizmet_toplam']:,.2f} {data['para_birimi']}</span>
                </div>
                <div class="flex justify-between text-slate-600">
                    <span>Toplam KDV:</span>
                    <span>{data['tutarlar']['kdv_toplam']:,.2f} {data['para_birimi']}</span>
                </div>
                <div class="flex justify-between font-bold text-base text-slate-900 border-t border-slate-200 pt-2">
                    <span>Ödenecek Tutar:</span>
                    <span class="text-emerald-600">{data['tutarlar']['odenecek_tutar']:,.2f} {data['para_birimi']}</span>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path

def main():
    parser = argparse.ArgumentParser(description="GİB UBL-TR e-Fatura & e-Arşiv XML Görüntüleyici")
    parser.add_argument("xml_path", help="İncelenecek e-Fatura/e-Arşiv XML dosyasının yolu")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON formatında verir")
    parser.add_argument("--html", action="store_true", help="Faturayı HTML dosyasına dönüştürür ve tarayıcıda açar")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not os.path.exists(args.xml_path):
        print(f"Hata: Dosya bulunamadı -> {args.xml_path}", file=sys.stderr)
        sys.exit(1)

    data = parse_ubl_invoice(args.xml_path)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if args.html:
        out_html = os.path.splitext(args.xml_path)[0] + ".html"
        generate_html_invoice(data, out_html)
        print(f"[OK] Fatura HTML olarak üretildi: {out_html}")
        webbrowser.open(out_html)
        return

    # Terminal çıktısı
    print("=" * 80)
    print(f"            GİB e-FATURA ÖZETİ: {data['fatura_no']} ({data['fatura_tipi']})")
    print("=" * 80)
    print(f"Tarih:        {data['fatura_tarihi']}")
    print(f"Satıcı:       {data['satici']['unvan']} (VKN/TCKN: {data['satici']['vkn_tckn']})")
    print(f"Alıcı:        {data['alici']['unvan']} (VKN/TCKN: {data['alici']['vkn_tckn']})")
    print("-" * 80)
    print(f"Mal/Hizmet:   {data['tutarlar']['mal_hizmet_toplam']:,.2f} {data['para_birimi']}")
    print(f"Toplam KDV:   {data['tutarlar']['kdv_toplam']:,.2f} {data['para_birimi']}")
    print(f"ÖDENECEK:     {data['tutarlar']['odenecek_tutar']:,.2f} {data['para_birimi']}")
    print("=" * 80)
    print("Tarayıcıda açmak için: python ubl_viewer.py fatura.xml --html")

if __name__ == "__main__":
    main()
