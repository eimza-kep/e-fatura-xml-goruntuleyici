#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GİB UBL-TR e-Fatura, e-Arşiv & e-İrsaliye XML Görüntüleyici v1.2
==============================================================
Bu betik, Gelir İdaresi Başkanlığı UBL-TR 1.2 standardındaki e-Fatura, e-Arşiv
ve e-İrsaliye (DespatchAdvice) XML dosyalarını ayrıştırarak; belge kalemlerini,
satıcı/alıcı ve taşıyıcı bilgilerini, KDV dağılımını terminalde gösterir veya
yazdırılabilir modern bir HTML faturası/irsaliyesi üretir.

Özellikler:
- e-Fatura, e-Arşiv ve e-İrsaliye (DespatchAdvice) desteği
- Sıfır harici bağımlılık (Pure Python Standard Library)
- KDV oran dağılımı (%1, %10, %20) detaylandırma
- Kalemleri muhasebe uyumlu CSV olarak dışa aktarma
- Yazdırılabilir (print-ready) ve responsive HTML görünümü
- Toplu dizin tarama (--dir) ve HTML fatura arşivi üretimi

Yazar: E-İmza & Dijital Dönüşüm Portalı (https://efaturabilgi.site/)
Lisans: MIT
"""

import sys
import os
import re
import csv
import json
import webbrowser
import argparse
import xml.etree.ElementTree as ET

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def clean_tag(tag):
    """XML etiketindeki isim alanını (namespace) temizler."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def parse_ubl_document(xml_path):
    """UBL-TR e-Fatura veya e-İrsaliye XML dosyasını ayrıştırır."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Hata: XML dosyası ayrıştırılamadı -> {e}", file=sys.stderr)
        sys.exit(1)

    root_tag = clean_tag(root.tag)
    is_despatch = "DespatchAdvice" in root_tag

    data = {
        "belge_turu": "e-İrsaliye" if is_despatch else "e-Fatura",
        "fatura_no": "",
        "fatura_tarihi": "",
        "fatura_tipi": "SEVK" if is_despatch else "SATIS",
        "para_birimi": "TRY",
        "satici": { "unvan": "", "vkn_tckn": "", "vergi_dairesi": "", "sehir": "" },
        "alici":  { "unvan": "", "vkn_tckn": "", "vergi_dairesi": "", "sehir": "" },
        "tasiyici": { "unvan": "", "vkn_tckn": "", "plaka": "" },
        "tutarlar": { "mal_hizmet_toplam": 0.0, "kdv_toplam": 0.0, "odenecek_tutar": 0.0 },
        "kdv_detaylari": [],
        "kalemler": []
    }

    # Ana meta veriler
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "").strip()

        if tag == "ID" and not data["fatura_no"]:
            data["fatura_no"] = val
        elif tag == "IssueDate" and not data["fatura_tarihi"]:
            data["fatura_tarihi"] = val
        elif tag == "InvoiceTypeCode" and not is_despatch and not data["fatura_tipi"]:
            data["fatura_tipi"] = val
        elif tag == "DespatchAdviceTypeCode" and is_despatch:
            data["fatura_tipi"] = val
        elif tag == "DocumentCurrencyCode" and not data["para_birimi"]:
            data["para_birimi"] = val

    # Satıcı / Gönderen (AccountingSupplierParty / DespatchSupplierParty)
    supplier_tags = {"AccountingSupplierParty", "DespatchSupplierParty"}
    for party in root.iter():
        if clean_tag(party.tag) in supplier_tags:
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not data["satici"]["unvan"]:
                    data["satici"]["unvan"] = cval
                elif ctag == "ID" and not data["satici"]["vkn_tckn"]:
                    data["satici"]["vkn_tckn"] = cval
                elif ctag == "CityName":
                    data["satici"]["sehir"] = cval

    # Alıcı (AccountingCustomerParty / DeliveryCustomerParty)
    customer_tags = {"AccountingCustomerParty", "DeliveryCustomerParty"}
    for party in root.iter():
        if clean_tag(party.tag) in customer_tags:
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not data["alici"]["unvan"]:
                    data["alici"]["unvan"] = cval
                elif ctag == "ID" and not data["alici"]["vkn_tckn"]:
                    data["alici"]["vkn_tckn"] = cval
                elif ctag == "CityName":
                    data["alici"]["sehir"] = cval

    # Taşıyıcı ve Plaka (e-İrsaliye için)
    for party in root.iter():
        if clean_tag(party.tag) in ["CarrierParty", "Shipment"]:
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not data["tasiyici"]["unvan"]:
                    data["tasiyici"]["unvan"] = cval
                elif ctag == "LicensePlateID" and not data["tasiyici"]["plaka"]:
                    data["tasiyici"]["plaka"] = cval

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

    # KDV Dağılımı (TaxSubtotal)
    for sub in root.iter():
        if clean_tag(sub.tag) == "TaxSubtotal":
            sub_kdv = 0.0
            sub_oran = 0.0
            for sc in sub.iter():
                sctag = clean_tag(sc.tag)
                scval = (sc.text or "0").replace(",", ".")
                if sctag == "TaxAmount":
                    try: sub_kdv = float(scval)
                    except: pass
                elif sctag == "Percent":
                    try: sub_oran = float(scval)
                    except: pass
            if sub_oran > 0 or sub_kdv > 0:
                data["kdv_detaylari"].append({"oran": sub_oran, "tutar": sub_kdv})

    # Kalemler (InvoiceLine veya DespatchLine)
    line_tags = {"InvoiceLine", "DespatchLine"}
    for line in root.iter():
        if clean_tag(line.tag) in line_tags:
            item_name = ""
            qty = 1.0
            price = 0.0
            total = 0.0
            for c in line.iter():
                ctag = clean_tag(c.tag)
                cval = (c.text or "").strip()
                if ctag in ["Name", "ItemDescription"] and not item_name:
                    item_name = cval
                elif ctag in ["InvoicedQuantity", "DeliveredQuantity"]:
                    try: qty = float(cval.replace(",", "."))
                    except: pass
                elif ctag == "PriceAmount":
                    try: price = float(cval.replace(",", "."))
                    except: pass
                elif ctag == "LineExtensionAmount":
                    try: total = float(cval.replace(",", "."))
                    except: pass
            if item_name:
                if total == 0 and price > 0:
                    total = qty * price
                data["kalemler"].append({
                    "urun": item_name,
                    "miktar": qty,
                    "fiyat": price,
                    "toplam": total
                })

    return data

# Geriye dönük uyumluluk
parse_ubl_invoice = parse_ubl_document

def generate_html_invoice(data, output_path):
    """UBL verisinden modern ve yazdırılabilir bir HTML belgesi üretir."""
    kalemler_tr = ""
    for idx, k in enumerate(data["kalemler"]):
        kalemler_tr += f"""
        <tr class="border-b border-slate-100 text-sm hover:bg-slate-50 transition">
            <td class="py-2.5 px-3 text-slate-500">{idx+1}</td>
            <td class="py-2.5 px-3 font-medium text-slate-800">{k['urun']}</td>
            <td class="py-2.5 px-3 text-right">{k['miktar']:g}</td>
            <td class="py-2.5 px-3 text-right">{k['fiyat']:,.2f} {data['para_birimi']}</td>
            <td class="py-2.5 px-3 text-right font-semibold text-slate-900">{k['toplam']:,.2f} {data['para_birimi']}</td>
        </tr>
        """

    kdv_rows = ""
    for kd in data["kdv_detaylari"]:
        kdv_rows += f"""
        <div class="flex justify-between text-xs text-slate-500">
            <span>KDV (%{kd['oran']:g}):</span>
            <span>{kd['tutar']:,.2f} {data['para_birimi']}</span>
        </div>
        """

    tasiyici_html = ""
    if data["tasiyici"]["unvan"] or data["tasiyici"]["plaka"]:
        tasiyici_html = f"""
        <div class="bg-amber-50 p-4 rounded-xl border border-amber-200 col-span-2 text-xs">
            <span class="font-bold text-amber-800 uppercase block mb-1">🚚 SEVK VE TAŞIYICI BİLGİLERİ</span>
            <p><strong>Taşıyıcı:</strong> {data['tasiyici']['unvan'] or 'Belirtilmemiş'} | <strong>Araç Plaka:</strong> {data['tasiyici']['plaka'] or 'Belirtilmemiş'}</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['belge_turu']}: {data['fatura_no']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ background: #fff !important; padding: 0 !important; }}
            .invoice-card {{ box-shadow: none !important; border: none !important; max-width: 100% !important; }}
        }}
    </style>
</head>
<body class="bg-slate-100 text-slate-800 p-4 sm:p-8">
    <div class="max-w-3xl mx-auto mb-4 flex justify-between items-center no-print">
        <span class="text-xs text-slate-500 font-mono">UBL-TR 1.2 Dokümanı</span>
        <button onclick="window.print()" class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-4 py-2 rounded-xl text-sm shadow-sm transition">
            🖨️ Yazdır / PDF Olarak Kaydet
        </button>
    </div>

    <div class="invoice-card max-w-3xl mx-auto bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <div class="flex justify-between items-start border-b border-slate-200 pb-6">
            <div>
                <span class="bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                    {data['belge_turu']} ({data['fatura_tipi']})
                </span>
                <h1 class="text-2xl font-black text-slate-900 mt-2">{data['fatura_no'] or 'İSİMSİZ BELGE'}</h1>
                <p class="text-xs text-slate-500 mt-0.5">Düzenleme Tarihi: {data['fatura_tarihi'] or 'Belirtilmemiş'}</p>
            </div>
            <div class="text-right">
                <span class="text-xs text-slate-400 font-bold block uppercase">Ödenecek Tutar</span>
                <span class="text-3xl font-extrabold text-emerald-600">{data['tutarlar']['odenecek_tutar']:,.2f} {data['para_birimi']}</span>
            </div>
        </div>

        <div class="grid grid-cols-2 gap-4 my-6 text-sm">
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">GÖNDEREN / SATICI</span>
                <p class="font-bold text-slate-900">{data['satici']['unvan'] or 'Belirtilmemiş'}</p>
                <p class="text-xs text-slate-600 mt-1">VKN/TCKN: <span class="font-mono">{data['satici']['vkn_tckn']}</span></p>
                <p class="text-xs text-slate-500">{data['satici']['sehir']}</p>
            </div>
            <div class="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">ALICI / MÜŞTERİ</span>
                <p class="font-bold text-slate-900">{data['alici']['unvan'] or 'Belirtilmemiş'}</p>
                <p class="text-xs text-slate-600 mt-1">VKN/TCKN: <span class="font-mono">{data['alici']['vkn_tckn']}</span></p>
                <p class="text-xs text-slate-500">{data['alici']['sehir']}</p>
            </div>
            {tasiyici_html}
        </div>

        <table class="w-full text-left border-collapse my-6">
            <thead>
                <tr class="border-b border-slate-200 text-xs text-slate-400 uppercase tracking-wider">
                    <th class="py-2 px-3">#</th>
                    <th class="py-2 px-3">Mal / Hizmet Açıklaması</th>
                    <th class="py-2 px-3 text-right">Miktar</th>
                    <th class="py-2 px-3 text-right">Birim Fiyat</th>
                    <th class="py-2 px-3 text-right">Toplam Tutar</th>
                </tr>
            </thead>
            <tbody>
                {kalemler_tr or '<tr><td colspan="5" class="py-4 text-center text-slate-400 text-sm">Detay kalem bulunamadı.</td></tr>'}
            </tbody>
        </table>

        <div class="border-t border-slate-200 pt-4 flex justify-end">
            <div class="w-72 space-y-1.5 text-sm">
                <div class="flex justify-between text-slate-600">
                    <span>Mal/Hizmet Toplamı:</span>
                    <span>{data['tutarlar']['mal_hizmet_toplam']:,.2f} {data['para_birimi']}</span>
                </div>
                {kdv_rows}
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

def export_csv_items(data, output_path):
    """Fatura ve irsaliye kalemlerini muhasebe CSV formatında dışa aktarır."""
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Sıra", "Belge No", "Belge Türü", "Tarih", "Satıcı VKN", "Alıcı VKN", "Ürün/Hizmet Açıklaması", "Miktar", "Birim Fiyat", "Toplam Tutar", "Para Birimi"])
        for idx, item in enumerate(data.get("kalemler", []), 1):
            writer.writerow([
                idx,
                data.get("fatura_no", ""),
                data.get("belge_turu", ""),
                data.get("fatura_tarihi", ""),
                data.get("satici", {}).get("vkn_tckn", ""),
                data.get("alici", {}).get("vkn_tckn", ""),
                item.get("urun", ""),
                item.get("miktar", 1),
                item.get("fiyat", 0.0),
                item.get("toplam", 0.0),
                data.get("para_birimi", "TRY")
            ])
    return output_path

def main():
    parser = argparse.ArgumentParser(description="GİB UBL-TR e-Fatura, e-Arşiv & e-İrsaliye XML Görüntüleyici v1.2")
    parser.add_argument("xml_path", nargs="?", default=None, help="İncelenecek XML dosyasının yolu")
    parser.add_argument("--dir", help="Dizindeki tüm XML e-belgeleri toplu inceler")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON formatında verir")
    parser.add_argument("--csv", action="store_true", help="Belge kalemlerini CSV formatında dışa aktarır")
    parser.add_argument("--html", action="store_true", help="Belgeyi HTML dosyasına dönüştürür")
    parser.add_argument("--output", help="HTML, JSON veya CSV çıktısının kaydedileceği özel dosya yolu")
    parser.add_argument("--no-browser", action="store_true", help="HTML üretirken tarayıcıyı otomatik açmaz")

    args = parser.parse_args()

    if not args.xml_path and not args.dir:
        parser.print_help()
        sys.exit(0)

    if args.dir:
        if not os.path.isdir(args.dir):
            print(f"Hata: Dizin bulunamadı -> {args.dir}", file=sys.stderr)
            sys.exit(1)
        files = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.lower().endswith(".xml")]
        all_docs = []
        for fp in sorted(files):
            try:
                all_docs.append(parse_ubl_document(fp))
            except Exception:
                pass
        
        if args.csv:
            out_c = args.output or "toplu_kalemler.csv"
            with open(out_c, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Sıra", "Belge No", "Tür", "Tarih", "Satıcı", "Alıcı", "Ödenecek", "Para Birimi"])
                for idx, doc in enumerate(all_docs, 1):
                    writer.writerow([idx, doc["fatura_no"], doc["belge_turu"], doc["fatura_tarihi"], doc["satici"]["unvan"], doc["alici"]["unvan"], doc["tutarlar"]["odenecek_tutar"], doc["para_birimi"]])
            print(f"[OK] Toplu belge özeti kaydedildi: {out_c}")
            return
        elif args.json:
            print(json.dumps(all_docs, ensure_ascii=False, indent=2))
            return
        else:
            print("=" * 80)
            print(f"Toplam {len(all_docs)} Adet e-Belge İncelendi:")
            print("=" * 80)
            for d in all_docs:
                print(f"📄 [{d['belge_turu']}] {d['fatura_no']:<16} | {d['fatura_tarihi']} | {d['satici']['unvan'][:25]:<25} | {d['tutarlar']['odenecek_tutar']:>10,.2f} {d['para_birimi']}")
            print("=" * 80)
            return

    if not os.path.exists(args.xml_path):
        print(f"Hata: Dosya bulunamadı -> {args.xml_path}", file=sys.stderr)
        sys.exit(1)

    data = parse_ubl_document(args.xml_path)

    if args.output:
        if args.output.lower().endswith(".json") or args.json:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[OK] Belge verisi JSON olarak kaydedildi: {args.output}")
            return
        elif args.output.lower().endswith(".csv") or args.csv:
            export_csv_items(data, args.output)
            print(f"[OK] Belge kalemleri CSV olarak kaydedildi: {args.output}")
            return
        elif args.output.lower().endswith(".html") or args.html:
            generate_html_invoice(data, args.output)
            print(f"[OK] Belge HTML olarak kaydedildi: {args.output}")
            if not args.no_browser:
                webbrowser.open(args.output)
            return

    if args.csv:
        out_csv = os.path.splitext(args.xml_path)[0] + "_kalemler.csv"
        export_csv_items(data, out_csv)
        print(f"[OK] Belge kalemleri CSV olarak üretildi: {out_csv}")
        return

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if args.html:
        out_html = os.path.splitext(args.xml_path)[0] + ".html"
        generate_html_invoice(data, out_html)
        print(f"[OK] Belge HTML olarak üretildi: {out_html}")
        if not args.no_browser:
            webbrowser.open(out_html)
        return

    # Terminal çıktısı
    print("=" * 80)
    print(f"       GİB {data['belge_turu'].upper()} ÖZETİ: {data['fatura_no'] or 'İSİMSİZ'} ({data['fatura_tipi']})")
    print("=" * 80)
    print(f"Tarih:        {data['fatura_tarihi']}")
    print(f"Satıcı:       {data['satici']['unvan']} (VKN/TCKN: {data['satici']['vkn_tckn']})")
    print(f"Alıcı:        {data['alici']['unvan']} (VKN/TCKN: {data['alici']['vkn_tckn']})")
    if data["tasiyici"]["unvan"] or data["tasiyici"]["plaka"]:
        print(f"Taşıyıcı:     {data['tasiyici']['unvan']} | Plaka: {data['tasiyici']['plaka']}")
    print("-" * 80)

    if data["kalemler"]:
        print(f"Kalemler ({len(data['kalemler'])} Adet):")
        for idx, k in enumerate(data["kalemler"]):
            print(f"  [{idx+1}] {k['urun']:<35} | Miktar: {k['miktar']:<4} | Toplam: {k['toplam']:,.2f} {data['para_birimi']}")
        print("-" * 80)

    print(f"Mal/Hizmet:   {data['tutarlar']['mal_hizmet_toplam']:,.2f} {data['para_birimi']}")
    if data["kdv_detaylari"]:
        for kd in data["kdv_detaylari"]:
            print(f"  └─ KDV (%{kd['oran']:g}): {kd['tutar']:,.2f} {data['para_birimi']}")
    print(f"Toplam KDV:   {data['tutarlar']['kdv_toplam']:,.2f} {data['para_birimi']}")
    print(f"ÖDENECEK:     {data['tutarlar']['odenecek_tutar']:,.2f} {data['para_birimi']}")
    print("=" * 80)
    print("Tarayıcıda görselleştirmek için: python ubl_viewer.py fatura.xml --html")

if __name__ == "__main__":
    main()
