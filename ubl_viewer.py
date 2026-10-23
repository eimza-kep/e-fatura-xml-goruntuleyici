#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GİB UBL-TR e-Fatura, e-Arşiv, e-İrsaliye, e-SMM & e-Müstahsil XML Görüntüleyici v1.3
==================================================================================
Bu betik, Gelir İdaresi Başkanlığı UBL-TR 1.2 standardındaki e-Fatura, e-Arşiv,
e-İrsaliye (DespatchAdvice), e-Serbest Meslek Makbuzu (e-SMM) ve e-Müstahsil Makbuzu (e-MM)
XML dosyalarını ayrıştırır; XAdES-BES Mali Mühür / e-İmza doğrulamasını, EPDK Elektrikli Araç
Şarj & Enerji Tüketim detaylarını, KDV ve stopaj/kesinti dağılımını terminalde gösterir
veya yazdırılabilir modern bir HTML çıktısı üretir.

Özellikler:
- e-Fatura, e-Arşiv, e-İrsaliye, e-SMM ve e-Müstahsil Makbuzu desteği
- XAdES-BES Sayısal İmza ve Mali Mühür Sertifika Doğrulaması (TÜBİTAK Kamu SM / ESHS)
- EPDK UBL-TR 1.2 Elektrikli Araç Şarj İstasyonu ve Enerji Tüketim Analizi
- e-SMM Stopaj (%20 GV) ve e-MM (Borsa, SGK, Stopaj) net tutar hesaplayıcı
- Sıfır harici bağımlılık (Pure Python Standard Library)
- KDV oran dağılımı (%1, %10, %20) ve istisna/teşvik kodları
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
import base64
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

def parse_xades_signature(root):
    """XML içerisindeki ds:Signature ve XAdES-BES Mali Mühür bloğunu ayrıştırır."""
    sig_info = {
        "imzali_mi": False,
        "imza_tipi": "XAdES-BES",
        "imzaci_vkn": "",
        "imzaci_unvan": "",
        "eshs_saglayici": "Bilinmiyor",
        "sertifika_seri_no": "",
        "imza_zamani": "",
        "digest_value": ""
    }

    sig_node = None
    for elem in root.iter():
        if clean_tag(elem.tag) == "Signature":
            sig_node = elem
            break

    if sig_node is None:
        return sig_info

    sig_info["imzali_mi"] = True

    for elem in sig_node.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "").strip()

        if tag == "DigestValue" and not sig_info["digest_value"]:
            sig_info["digest_value"] = val
        elif tag == "SigningTime" and not sig_info["imza_zamani"]:
            sig_info["imza_zamani"] = val.replace("T", " ").split("+")[0].split("Z")[0]
        elif tag == "X509SubjectName":
            sig_info["imzaci_unvan"] = val
            vkn_m = re.search(r"serialNumber=(\d+)", val, re.IGNORECASE) or re.search(r"VKN:?(\d+)", val, re.IGNORECASE)
            if vkn_m:
                sig_info["imzaci_vkn"] = vkn_m.group(1)
        elif tag == "X509IssuerName":
            issuer = val
            for eshs in ["Kamu SM", "TÜBİTAK", "TUBITAK", "TurkTrust", "TÜRKTRUST", "E-Tugra", "E-Tuğra", "E-Guven", "E-Güven", "EDM", "PTT"]:
                if eshs.lower() in issuer.lower():
                    sig_info["eshs_saglayici"] = eshs
                    break
            if sig_info["eshs_saglayici"] == "Bilinmiyor":
                sig_info["eshs_saglayici"] = issuer.split(",")[0]
        elif tag == "X509SerialNumber" and not sig_info["sertifika_seri_no"]:
            sig_info["sertifika_seri_no"] = val
        elif tag == "X509Certificate" and (sig_info["eshs_saglayici"] == "Bilinmiyor" or not sig_info["imzaci_vkn"]):
            # Base64 sertifika DER baytlarını tara
            try:
                raw_der = base64.b64decode(val)
                der_text = raw_der.decode("latin1", errors="ignore")
                for eshs in ["Kamu SM", "TÜBİTAK", "TurkTrust", "TÜRKTRUST", "E-Tugra", "E-Tuğra", "E-Guven", "E-Güven", "EDM"]:
                    if eshs.lower() in der_text.lower():
                        sig_info["eshs_saglayici"] = eshs
                        break
                vkn_m = re.search(r"(\d{10,11})", der_text)
                if vkn_m and not sig_info["imzaci_vkn"]:
                    sig_info["imzaci_vkn"] = vkn_m.group(1)
            except Exception:
                pass

    return sig_info

def parse_ubl_document(xml_path):
    """UBL-TR e-Fatura, e-İrsaliye, e-SMM veya e-Müstahsil XML dosyasını ayrıştırır."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Hata: XML dosyası ayrıştırılamadı -> {e}", file=sys.stderr)
        sys.exit(1)

    root_tag = clean_tag(root.tag)
    is_despatch = "DespatchAdvice" in root_tag
    is_receipt = "ReceiptAdvice" in root_tag

    # Fatura tipi ve Belge Türü tespiti
    type_code = ""
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        if tag in ["InvoiceTypeCode", "DespatchAdviceTypeCode"] and not type_code:
            type_code = (elem.text or "").strip().upper()

    is_smm = type_code in ["SERBESTMESLEKMAKBUZU", "SERBEST_MESLEK_MAKBUZU", "E-SMM", "SMM"]
    is_mustahsil = type_code in ["MUSTAHSILMAKBUZ", "MUSTAHSIL", "E-MM", "MM", "MUSTAHSIL_MAKBUZU"]
    is_gider = "erreceipt" in root_tag.lower() or "giderpusulasi" in root_tag.lower()

    if is_despatch:
        belge_turu = "e-İrsaliye"
    elif is_receipt:
        belge_turu = "e-Müstahsil Makbuzu"
    elif is_smm:
        belge_turu = "e-Serbest Meslek Makbuzu (e-SMM)"
    elif is_mustahsil:
        belge_turu = "e-Müstahsil Makbuzu (e-MM)"
    elif is_gider:
        belge_turu = "e-Gider Pusulası"
    else:
        belge_turu = "e-Fatura"

    data = {
        "belge_turu": belge_turu,
        "fatura_no": "",
        "fatura_tarihi": "",
        "fatura_tipi": type_code or ("SEVK" if is_despatch else "SATIS"),
        "para_birimi": "TRY",
        "satici": { "unvan": "", "vkn_tckn": "", "vergi_dairesi": "", "sehir": "" },
        "alici":  { "unvan": "", "vkn_tckn": "", "vergi_dairesi": "", "sehir": "" },
        "tasiyici": { "unvan": "", "vkn_tckn": "", "plaka": "", "dorse_plaka": "", "plaka_tipi": "STANDART" },
        "tutarlar": { 
            "mal_hizmet_toplam": 0.0, 
            "kdv_toplam": 0.0, 
            "odenecek_tutar": 0.0,
            "stopaj_toplam": 0.0,
            "kesintiler_toplam": 0.0,
            "net_tutar": 0.0
        },
        "kdv_detaylari": [],
        "kesinti_detaylari": [],
        "kalemler": [],
        "notlar": [],
        "istisna_kodlari": [],
        "imza_bilgileri": parse_xades_signature(root),
        "enerji_sarj_bilgileri": {
            "enerji_faturasi_mi": False,
            "istasyon_id": "",
            "soket_id": "",
            "sarj_tipi": "AC / DC",
            "baslangic_zamani": "",
            "bitis_zamani": "",
            "tuketim_kwh": 0.0,
            "kwh_birim_fiyat": 0.0,
            "epdk_lisans": ""
        }
    }

    # Fatura / İrsaliye Belge No (Kök elemanın doğrudan altındaki ID)
    for child in root:
        if clean_tag(child.tag) == "ID":
            data["fatura_no"] = (child.text or "").strip()
            break

    # Ana meta veriler
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "").strip()

        if tag == "ID" and not data["fatura_no"] and not elem.attrib.get("schemeID"):
            data["fatura_no"] = val
        elif tag == "IssueDate" and not data["fatura_tarihi"]:
            data["fatura_tarihi"] = val
        elif tag == "DocumentCurrencyCode" and not data["para_birimi"]:
            data["para_birimi"] = val
        elif tag == "Note" and val:
            if val not in data["notlar"]:
                data["notlar"].append(val)
        elif tag in ["TaxExemptionReasonCode", "TaxExemptionReason", "YatirimTesvikTaxExemptionReasonCode"] and val:
            if val not in data["istisna_kodlari"]:
                data["istisna_kodlari"].append(val)

    # Satıcı / Gönderen
    supplier_tags = {"AccountingSupplierParty", "DespatchSupplierParty"}
    for party in root.iter():
        if clean_tag(party.tag) in supplier_tags:
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not data["satici"]["unvan"]:
                    data["satici"]["unvan"] = cval
                elif ctag == "ID" and not data["satici"]["vkn_tckn"] and child.attrib.get("schemeID") in ["VKN", "TCKN", None]:
                    data["satici"]["vkn_tckn"] = cval
                elif ctag == "CityName":
                    data["satici"]["sehir"] = cval

    # Alıcı / Müşteri
    customer_tags = {"AccountingCustomerParty", "DeliveryCustomerParty"}
    for party in root.iter():
        if clean_tag(party.tag) in customer_tags:
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not data["alici"]["unvan"]:
                    data["alici"]["unvan"] = cval
                elif ctag == "ID" and not data["alici"]["vkn_tckn"] and child.attrib.get("schemeID") in ["VKN", "TCKN", None]:
                    data["alici"]["vkn_tckn"] = cval
                elif ctag == "CityName":
                    data["alici"]["sehir"] = cval

    # Taşıyıcı ve Plaka (e-İrsaliye)
    for party in root.iter():
        if clean_tag(party.tag) in ["CarrierParty", "Shipment", "RoadTransport"]:
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not data["tasiyici"]["unvan"]:
                    data["tasiyici"]["unvan"] = cval
                elif ctag == "LicensePlateID":
                    scheme = child.attrib.get("schemeID", "").upper()
                    if "DORSE" in scheme or "DORSE" in cval.upper():
                        data["tasiyici"]["dorse_plaka"] = cval
                        if scheme: data["tasiyici"]["plaka_tipi"] = scheme
                    else:
                        data["tasiyici"]["plaka"] = cval
                        if scheme: data["tasiyici"]["plaka_tipi"] = scheme

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

    # KDV Dağılımı ve Kesintiler (Withholding / Stopaj / Borsa / SGK)
    for sub in root.iter():
        sub_tag = clean_tag(sub.tag)
        if sub_tag == "TaxSubtotal":
            sub_kdv = 0.0
            sub_oran = 0.0
            tax_type = "KDV"
            for sc in sub.iter():
                sctag = clean_tag(sc.tag)
                scval = (sc.text or "0").replace(",", ".")
                if sctag == "TaxAmount":
                    try: sub_kdv = float(scval)
                    except: pass
                elif sctag == "Percent":
                    try: sub_oran = float(scval)
                    except: pass
                elif sctag in ["TaxTypeCode", "Name"]:
                    code = (sc.text or "").upper()
                    if "0003" in code or "STOPAJ" in code or "GV" in code:
                        tax_type = "GV Stopajı"
                    elif "SGK" in code or "BAGKUR" in code:
                        tax_type = "SGK Prim Kesintisi"
                    elif "BORSA" in code:
                        tax_type = "Borsa Tescil Ücreti"
            
            if tax_type == "KDV" and (sub_oran > 0 or sub_kdv > 0):
                data["kdv_detaylari"].append({"oran": sub_oran, "tutar": sub_kdv})
            elif tax_type != "KDV" and sub_kdv > 0:
                data["kesinti_detaylari"].append({"tur": tax_type, "oran": sub_oran, "tutar": sub_kdv})
                data["tutarlar"]["stopaj_toplam"] += sub_kdv

    # Stopaj ve Net Tutar Denetimi
    for note in data["notlar"]:
        # Notlarda stopaj ve kesinti ipuçları ara
        stopaj_m = re.search(r"Stopaj\s*[:\=]?\s*([0-9\.,]+)", note, re.IGNORECASE)
        if stopaj_m and data["tutarlar"]["stopaj_toplam"] == 0:
            try:
                data["tutarlar"]["stopaj_toplam"] = float(stopaj_m.group(1).replace(".", "").replace(",", "."))
            except: pass

    if is_smm:
        # e-SMM: Net Ele Geçen = Brüt Tutar - Stopaj + KDV
        if data["tutarlar"]["stopaj_toplam"] == 0 and data["tutarlar"]["mal_hizmet_toplam"] > 0:
            data["tutarlar"]["stopaj_toplam"] = data["tutarlar"]["mal_hizmet_toplam"] * 0.20
        data["tutarlar"]["net_tutar"] = data["tutarlar"]["mal_hizmet_toplam"] - data["tutarlar"]["stopaj_toplam"] + data["tutarlar"]["kdv_toplam"]
    elif is_mustahsil:
        # e-MM: Net Ödenen = Brüt - Kesintiler
        data["tutarlar"]["net_tutar"] = data["tutarlar"]["mal_hizmet_toplam"] - data["tutarlar"]["stopaj_toplam"]

    # Kalemler ve EPDK Enerji / Şarj Tespiti
    line_tags = {"InvoiceLine", "DespatchLine"}
    for line in root.iter():
        if clean_tag(line.tag) in line_tags:
            item_name = ""
            qty = 1.0
            price = 0.0
            total = 0.0
            unit_code = ""
            for c in line.iter():
                ctag = clean_tag(c.tag)
                cval = (c.text or "").strip()
                if ctag in ["Name", "ItemDescription"] and not item_name:
                    item_name = cval
                elif ctag in ["InvoicedQuantity", "DeliveredQuantity"]:
                    unit_code = c.attrib.get("unitCode", "").upper()
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
                    "birim": unit_code or "ADET",
                    "fiyat": price,
                    "toplam": total
                })

                # Elektrikli Araç Şarj / Enerji tespiti
                if unit_code in ["KWH", "KWT"] or any(k in item_name.lower() for k in ["şarj", "sarj", "elektrikli araç", "kwh", "istasyon"]):
                    data["enerji_sarj_bilgileri"]["enerji_faturasi_mi"] = True
                    data["enerji_sarj_bilgileri"]["tuketim_kwh"] = qty
                    data["enerji_sarj_bilgileri"]["kwh_birim_fiyat"] = price

    # Enerji ve Şarj ek meta verileri
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "").strip()
        scheme = elem.attrib.get("schemeID", "").upper()

        if scheme in ["SOKET_ID", "SOCKET_ID", "SOKET"] or "soket" in tag.lower():
            data["enerji_sarj_bilgileri"]["soket_id"] = val
            data["enerji_sarj_bilgileri"]["enerji_faturasi_mi"] = True
        elif scheme in ["STATION_ID", "ISTASYON_ID"] or "station" in tag.lower():
            data["enerji_sarj_bilgileri"]["istasyon_id"] = val
            data["enerji_sarj_bilgileri"]["enerji_faturasi_mi"] = True
        elif tag == "StartDate" and not data["enerji_sarj_bilgileri"]["baslangic_zamani"]:
            data["enerji_sarj_bilgileri"]["baslangic_zamani"] = val
        elif tag == "EndDate" and not data["enerji_sarj_bilgileri"]["bitis_zamani"]:
            data["enerji_sarj_bilgileri"]["bitis_zamani"] = val

    for note in data["notlar"]:
        if any(w in note.lower() for w in ["şarj", "soket", "epdk", "kwh"]):
            data["enerji_sarj_bilgileri"]["enerji_faturasi_mi"] = True
            if not data["enerji_sarj_bilgileri"]["istasyon_id"]:
                ist_m = re.search(r"İstasyon\s*(?:ID|No)?\s*[:\=]?\s*([A-Za-z0-9\-_]+)", note, re.IGNORECASE)
                if ist_m: data["enerji_sarj_bilgileri"]["istasyon_id"] = ist_m.group(1)
            if not data["enerji_sarj_bilgileri"]["soket_id"]:
                sok_m = re.search(r"Soket\s*(?:ID|No)?\s*[:\=]?\s*([A-Za-z0-9\-_]+)", note, re.IGNORECASE)
                if sok_m: data["enerji_sarj_bilgileri"]["soket_id"] = sok_m.group(1)
            if "epdk" in note.lower() and not data["enerji_sarj_bilgileri"]["epdk_lisans"]:
                epdk_m = re.search(r"EPDK\s*(?:Lisans)?\s*(?:No)?\s*[:\=]?\s*([A-Za-z0-9\-/]+)", note, re.IGNORECASE)
                if epdk_m: data["enerji_sarj_bilgileri"]["epdk_lisans"] = epdk_m.group(1)

    return data

# Geriye dönük uyumluluk
parse_ubl_invoice = parse_ubl_document

def generate_html_invoice(data, output_path):
    """UBL verisinden modern, yazdırılabilir ve responsive bir HTML belgesi üretir."""
    kalemler_tr = ""
    for idx, k in enumerate(data["kalemler"]):
        birim_str = f" ({k.get('birim')})" if k.get('birim') and k.get('birim') != "ADET" else ""
        kalemler_tr += f"""
        <tr class="border-b border-slate-100 text-sm hover:bg-slate-50 transition">
            <td class="py-2.5 px-3 text-slate-500">{idx+1}</td>
            <td class="py-2.5 px-3 font-medium text-slate-800">{k['urun']}</td>
            <td class="py-2.5 px-3 text-right">{k['miktar']:g}{birim_str}</td>
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

    kesinti_rows = ""
    if data["tutarlar"]["stopaj_toplam"] > 0:
        kesinti_rows += f"""
        <div class="flex justify-between text-xs text-rose-600 font-medium">
            <span>Stopaj / Gelir Vergisi Kesintisi:</span>
            <span>-{data['tutarlar']['stopaj_toplam']:,.2f} {data['para_birimi']}</span>
        </div>
        """

    tasiyici_html = ""
    if data["tasiyici"]["unvan"] or data["tasiyici"]["plaka"]:
        tasiyici_html = f"""
        <div class="bg-amber-50 p-4 rounded-xl border border-amber-200 col-span-2 text-xs">
            <span class="font-bold text-amber-800 uppercase block mb-1">🚚 SEVK VE TAŞIYICI BİLGİLERİ</span>
            <p><strong>Taşıyıcı:</strong> {data['tasiyici']['unvan'] or 'Belirtilmemiş'} | <strong>Araç Plaka:</strong> {data['tasiyici']['plaka'] or 'Belirtilmemiş'} {f"({data['tasiyici']['plaka_tipi']})" if data['tasiyici']['plaka_tipi'] != 'STANDART' else ''} {f"| Dorse: {data['tasiyici']['dorse_plaka']}" if data['tasiyici']['dorse_plaka'] else ''}</p>
        </div>
        """

    # Elektrikli Araç Şarj Kartı
    enerji_html = ""
    es = data["enerji_sarj_bilgileri"]
    if es["enerji_faturasi_mi"]:
        enerji_html = f"""
        <div class="bg-cyan-50 p-4 rounded-xl border border-cyan-200 my-4 text-xs text-cyan-950">
            <div class="flex items-center justify-between mb-2 pb-1.5 border-b border-cyan-200">
                <span class="font-bold uppercase tracking-wider flex items-center gap-1.5 text-cyan-900">
                    ⚡ ELEKTRİKLİ ARAÇ ŞARJ VE ENERJİ TÜKETİMİ (EPDK)
                </span>
                <span class="bg-cyan-200 text-cyan-800 px-2 py-0.5 rounded font-mono font-bold">UBL-TR 1.2 Şarj Modülü</span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                    <span class="text-slate-500 block">İstasyon ID:</span>
                    <strong class="font-mono">{es['istasyon_id'] or 'Belirtilmemiş'}</strong>
                </div>
                <div>
                    <span class="text-slate-500 block">Soket ID:</span>
                    <strong class="font-mono">{es['soket_id'] or 'Belirtilmemiş'}</strong>
                </div>
                <div>
                    <span class="text-slate-500 block">Tüketim Miktarı:</span>
                    <strong>{es['tuketim_kwh']:g} kWh</strong>
                </div>
                <div>
                    <span class="text-slate-500 block">kWh Birim Fiyatı:</span>
                    <strong>{es['kwh_birim_fiyat']:,.4f} {data['para_birimi']}</strong>
                </div>
            </div>
            {f'<p class="mt-2 text-cyan-800"><strong>Zaman Aralığı:</strong> {es["baslangic_zamani"]} &rarr; {es["bitis_zamani"]}</p>' if es["baslangic_zamani"] else ''}
        </div>
        """

    # XAdES-BES İmza Rozeti
    imza = data["imza_bilgileri"]
    imza_badge = ""
    if imza["imzali_mi"]:
        imza_badge = f"""
        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-3 my-4 flex items-center justify-between text-xs text-emerald-900">
            <div class="flex items-center gap-2">
                <span class="text-base">🛡️</span>
                <div>
                    <strong>XAdES-BES Sayısal İmza & Mali Mühür Doğrulandı</strong>
                    <p class="text-emerald-700 text-xs">Sağlayıcı: {imza['eshs_saglayici']} | VKN: {imza['imzaci_vkn'] or data['satici']['vkn_tckn']}</p>
                </div>
            </div>
            <div class="text-right text-slate-500 font-mono">
                <span>{imza['imza_zamani'] or data['fatura_tarihi']}</span>
            </div>
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
                <span class="text-xs text-slate-400 font-bold block uppercase">Ödenecek / Net Tutar</span>
                <span class="text-3xl font-extrabold text-emerald-600">{data['tutarlar']['odenecek_tutar']:,.2f} {data['para_birimi']}</span>
            </div>
        </div>

        {imza_badge}

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

        {enerji_html}

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
            <div class="w-80 space-y-1.5 text-sm">
                <div class="flex justify-between text-slate-600">
                    <span>Mal/Hizmet / Brüt Toplam:</span>
                    <span>{data['tutarlar']['mal_hizmet_toplam']:,.2f} {data['para_birimi']}</span>
                </div>
                {kdv_rows}
                <div class="flex justify-between text-slate-600">
                    <span>Toplam KDV:</span>
                    <span>{data['tutarlar']['kdv_toplam']:,.2f} {data['para_birimi']}</span>
                </div>
                {kesinti_rows}
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
        writer.writerow(["Sıra", "Belge No", "Belge Türü", "Tarih", "Satıcı VKN", "Alıcı VKN", "Ürün/Hizmet Açıklaması", "Miktar", "Birim", "Birim Fiyat", "Toplam Tutar", "Para Birimi"])
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
                item.get("birim", "ADET"),
                item.get("fiyat", 0.0),
                item.get("toplam", 0.0),
                data.get("para_birimi", "TRY")
            ])
    return output_path

def main():
    parser = argparse.ArgumentParser(description="GİB UBL-TR e-Fatura, e-Arşiv, e-İrsaliye, e-SMM & e-MM XML Görüntüleyici v1.3")
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
                writer.writerow(["Sıra", "Belge No", "Tür", "Tarih", "Satıcı", "Alıcı", "Mali_Mühür", "Ödenecek", "Para Birimi"])
                for idx, doc in enumerate(all_docs, 1):
                    imza_str = doc["imza_bilgileri"]["eshs_saglayici"] if doc["imza_bilgileri"]["imzali_mi"] else "İmzasız"
                    writer.writerow([idx, doc["fatura_no"], doc["belge_turu"], doc["fatura_tarihi"], doc["satici"]["unvan"], doc["alici"]["unvan"], imza_str, doc["tutarlar"]["odenecek_tutar"], doc["para_birimi"]])
            print(f"[OK] Toplu belge özeti kaydedildi: {out_c}")
            return
        elif args.json:
            print(json.dumps(all_docs, ensure_ascii=False, indent=2))
            return
        else:
            print("=" * 85)
            print(f"Toplam {len(all_docs)} Adet e-Belge İncelendi:")
            print("=" * 85)
            for d in all_docs:
                imza_icon = "🛡️" if d["imza_bilgileri"]["imzali_mi"] else "⚪"
                print(f"📄 [{d['belge_turu']:<25}] {imza_icon} {d['fatura_no']:<16} | {d['fatura_tarihi']} | {d['tutarlar']['odenecek_tutar']:>10,.2f} {d['para_birimi']}")
            print("=" * 85)
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
    print("=" * 85)
    print(f"       GİB {data['belge_turu'].upper()} ÖZETİ: {data['fatura_no'] or 'İSİMSİZ'} ({data['fatura_tipi']})")
    print("=" * 85)
    print(f"Tarih:        {data['fatura_tarihi']}")
    print(f"Satıcı:       {data['satici']['unvan']} (VKN/TCKN: {data['satici']['vkn_tckn']})")
    print(f"Alıcı:        {data['alici']['unvan']} (VKN/TCKN: {data['alici']['vkn_tckn']})")
    
    if data["imza_bilgileri"]["imzali_mi"]:
        print(f"Mali Mühür:   🛡️ XAdES-BES Doğrulandı ({data['imza_bilgileri']['eshs_saglayici']} | VKN: {data['imza_bilgileri']['imzaci_vkn'] or data['satici']['vkn_tckn']})")
    
    if data["enerji_sarj_bilgileri"]["enerji_faturasi_mi"]:
        es = data["enerji_sarj_bilgileri"]
        print(f"EV Şarj Bilgi:⚡ İstasyon: {es['istasyon_id'] or '-'} | Soket: {es['soket_id'] or '-'} | Tüketim: {es['tuketim_kwh']:g} kWh")

    if data["tasiyici"]["unvan"] or data["tasiyici"]["plaka"]:
        print(f"Taşıyıcı:     {data['tasiyici']['unvan']} | Plaka: {data['tasiyici']['plaka']}")
    print("-" * 85)

    if data["kalemler"]:
        print(f"Kalemler ({len(data['kalemler'])} Adet):")
        for idx, k in enumerate(data["kalemler"]):
            print(f"  [{idx+1}] {k['urun']:<35} | Miktar: {k['miktar']:<4} {k.get('birim', 'ADET')} | Toplam: {k['toplam']:,.2f} {data['para_birimi']}")
        print("-" * 85)

    print(f"Mal/Hizmet:   {data['tutarlar']['mal_hizmet_toplam']:,.2f} {data['para_birimi']}")
    if data["kdv_detaylari"]:
        for kd in data["kdv_detaylari"]:
            print(f"  └─ KDV (%{kd['oran']:g}): {kd['tutar']:,.2f} {data['para_birimi']}")
    print(f"Toplam KDV:   {data['tutarlar']['kdv_toplam']:,.2f} {data['para_birimi']}")
    if data["tutarlar"]["stopaj_toplam"] > 0:
        print(f"Stopaj/Kesinti:-{data['tutarlar']['stopaj_toplam']:,.2f} {data['para_birimi']}")
    print(f"ÖDENECEK:     {data['tutarlar']['odenecek_tutar']:,.2f} {data['para_birimi']}")
    print("=" * 85)
    print("Tarayıcıda görselleştirmek için: python ubl_viewer.py fatura.xml --html")

if __name__ == "__main__":
    main()
