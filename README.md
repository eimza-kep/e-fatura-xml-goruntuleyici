# GİB UBL-TR e-Fatura, e-Arşiv, e-İrsaliye, e-SMM & e-MM XML Görüntüleyici 🧾✨

[![Python CI](https://github.com/eimza-kep/e-fatura-xml-goruntuleyici/actions/workflows/ci.yml/badge.svg)](https://github.com/eimza-kep/e-fatura-xml-goruntuleyici/actions)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Standart: UBL-TR 1.2](https://img.shields.io/badge/Standart-UBL--TR%201.2-red.svg)](https://ebelge.gib.gov.tr)
[![Bağımlılık: Yok](https://img.shields.io/badge/Dependencies-Zero--Dependency-success.svg)](https://github.com)
[![Blog](https://img.shields.io/badge/Rehber-e--Fatura%20At%C3%B6lyesi-emerald.svg)](https://efaturabilgi.site/)

Gelir İdaresi Başkanlığı (GİB) **UBL-TR 1.2 standardındaki e-Fatura, e-Arşiv, e-İrsaliye (DespatchAdvice), e-Serbest Meslek Makbuzu (e-SMM) ve e-Müstahsil Makbuzu (e-MM)** XML dosyalarını ayrıştırıp; XAdES-BES Mali Mühür doğrulamasını, EPDK Elektrikli Araç Şarj & Enerji Tüketim detaylarını, fatura kalemlerini, satıcı/alıcı/taşıyıcı bilgilerini ve KDV/stopaj dağılımını terminalde özetleyen, muhasebe CSV'sine aktaran ve tarayıcıda yazdırılabilir modern bir HTML faturası oluşturan açık kaynaklı Python aracıdır.

---

## ✨ Öne Çıkan Özellikler (v1.3)

* ⚡ **Sıfır Harici Bağımlılık (Zero-Dependency):** Java, Node.js veya harici Python modülü gerektirmeyen %100 saf Python standart kütüphanesi mimarisi.
* 🛡️ **XAdES-BES Sayısal İmza & Mali Mühür Doğrulama:** XML içindeki `<ds:Signature>` bloğunu tarayarak imzacının VKN'sini, sertifika sağlayıcısını (TÜBİTAK Kamu SM / ESHS), seri numarasını ve DigestValue bütünlüğünü doğrular.
* ⚖️ **e-SMM ve e-Müstahsil Makbuzu Desteği:**
  - **e-SMM:** Serbest meslek erbabı (avukat, mali müşavir, doktor) için %20 Gelir Vergisi stopajı ve net ele geçen tutar hesaplama.
  - **e-MM:** Çiftçiden yapılan alımlarda GV stopajı, Ticaret Borsası tescil ücreti ve SGK Bağ-Kur prim kesintilerini ayrıştırma.
* ⚡ **EPDK Elektrikli Araç Şarj & Enerji Tüketim Modülü:** Şarj ağı operatörlerinin düzenlediği faturalarda İstasyon ID, Soket ID, kWh tüketim miktarı, birim fiyat ve şarj başlangıç/bitiş zamanlarını ayrıştırıp özel kart olarak sunar.
* 🚚 **Lojistik ve e-İrsaliye Desteği:** Yabancı plaka/dorse tipleri (`YABANCIPLAKA`, `YABANCIDORSE`), taşıyıcı firma unvanı ve sevk kalemleri ayrıştırması.
* 🖨️ **Baskıya Hazır HTML:** Tailwind CSS destekli, yazdırma moduna özel (`@media print`) profesyonel fatura çıktısı.
* 📊 **Muhasebe CSV Dışa Aktarımı:** Kalemleri ERP ve muhasebe yazılımlarına aktarılabilir formatta dışa aktarma.
* 📁 **Toplu Dizin Tarama:** `--dir` parametresi ile klasördeki yüzlerce e-belgeyi tek komutla tarama ve özetleme.

---

## 🛠️ Kurulum ve Yerel Geliştirme (Local Setup)

### 1. Gereksinimler
- **Python 3.8+** (Python 3.10, 3.11 veya 3.12 önerilir)
- **Git**

### 2. Depoyu Klonlayın
```bash
git clone https://github.com/eimza-kep/e-fatura-xml-goruntuleyici.git
cd e-fatura-xml-goruntuleyici
```

### 3. Sanal Ortam Kurulumu (İsteğe Bağlı)
Araç sıfır bağımlılığa sahip olduğu için doğrudan çalıştırılabilir; izole ortam için:
```bash
python -m venv venv

# Windows üzerinde aktive etme:
venv\Scripts\activate

# Linux / macOS üzerinde aktive etme:
source venv/bin/activate
```

### 4. Birim Testleri Çalıştırın
Tüm testleri doğrulamak için:
```bash
python -m unittest test_ubl.py
```
*(8 test senaryosu ~0.005 saniyede tamamlanmalıdır)*

---

## 🚀 Komut Satırı Kullanım Kılavuzu (CLI)

### 1. Terminalde Belge Özeti ve Mali Mühür İncelemesi
```bash
python ubl_viewer.py fatura.xml
```

**Örnek v1.3 Çıktısı:**
```text
=====================================================================================
       GİB E-FATURA ÖZETİ: GIB2026000000042 (SATIS)
=====================================================================================
Tarih:        2026-09-24
Satıcı:       Örnek Bilişim ve E-Dönüşüm Hizmetleri A.Ş. (VKN/TCKN: 1234567890)
Alıcı:        Anadolu Teknoloji ve Lojistik Ltd. Şti. (VKN/TCKN: 9876543210)
Mali Mühür:   🛡️ XAdES-BES Doğrulandı (Kamu SM | VKN: 1234567890)
-------------------------------------------------------------------------------------
Kalemler (1 Adet):
  [1] Bulut E-İmza & KEP Entegrasyon Paketi | Miktar: 2    C62  | Toplam: 20,000.00 TRY
-------------------------------------------------------------------------------------
Mal/Hizmet:   20,000.00 TRY
  └─ KDV (%20): 4,000.00 TRY
Toplam KDV:   4,000.00 TRY
ÖDENECEK:     24,000.00 TRY
=====================================================================================
```

### 2. Elektrikli Araç Şarj ve e-SMM Belgelerini İnceleme
```bash
# Şarj istasyonu faturası
python ubl_viewer.py sarj_faturasi.xml

# Serbest Meslek Makbuzu (e-SMM)
python ubl_viewer.py smm_belgesi.xml
```

### 3. Tarayıcıda Açılabilir HTML Faturası Üretme
```bash
python ubl_viewer.py fatura.xml --html
```
*(Tarayıcınızda modern HTML fatura görünümü otomatik olarak açılır)*

### 4. Fatura Kalemlerini CSV Olarak Kaydetme
```bash
python ubl_viewer.py fatura.xml --csv
```

### 5. Klasördeki Belgeleri Toplu İnceleme (Batch Scan)
```bash
python ubl_viewer.py --dir ./gelen_faturalar/ --csv toplu_ozet.csv
```

---

## 🐍 Python Projelerinde Kütüphane Olarak Kullanım

```python
from ubl_viewer import parse_ubl_document, generate_html_invoice

# XML belgesini ayrıştır
belge = parse_ubl_document("fatura.xml")

print(f"Belge Türü: {belge['belge_turu']}")
print(f"Belge No:   {belge['fatura_no']}")
print(f"Mali Mühür: {belge['imza_bilgileri']['eshs_saglayici']}")

if belge["enerji_sarj_bilgileri"]["enerji_faturasi_mi"]:
    print(f"EV Şarj Tüketimi: {belge['enerji_sarj_bilgileri']['tuketim_kwh']} kWh")

# HTML çıktısı üret
generate_html_invoice(belge, "cikti.html")
```

---

## 🔗 E-Dönüşüm Açık Kaynak Ekosistemi

Bu araç [eimza-kep](https://github.com/eimza-kep) organizasyonunun açık kaynak e-dönüşüm araçları ekosisteminin bir parçasıdır:

* 🇹🇷 **[awesome-turkiye-e-donusum](https://github.com/eimza-kep/awesome-turkiye-e-donusum):** Türkiye E-Dönüşüm kütüphane, mevzuat ve araçlar listesi.
* 📊 **[gib-edefter-berat-xml-dogrulayici](https://github.com/eimza-kep/gib-edefter-berat-xml-dogrulayici):** e-Defter ve Berat XML dosyalarını şema ve bakiye doğrulama aracı.
* 📑 **[e-fatura-itiraz-ve-iade-scripti](https://github.com/eimza-kep/e-fatura-itiraz-ve-iade-scripti):** 8 günlük yasal itiraz süresi takip ve fatura iade tutanağı scripti.
* 📬 **[kep-adresi-dogrulayici](https://github.com/eimza-kep/kep-adresi-dogrulayici):** KEP adresi ve BTK operatör denetleyici.
* 📜 **[python-pdf-eimza-dogrulayici](https://github.com/eimza-kep/python-pdf-eimza-dogrulayici):** PAdES/CAdES PDF dijital imza ve LTV doğrulama aracı.

---

## 📚 İlgili Teknik Rehberler
* 📄 [e-Fatura ve e-Arşiv Fatura Arasındaki Temel Hukuki ve Teknik Farklar](https://efaturabilgi.site/yazilar/e-fatura-ve-e-arsiv-arasindaki-farklar.html)
* 📄 [e-İrsaliye Zorunluluğu ve Sevk Sürecinde Karekod Uygulaması](https://edonusumkobi.site/yazilar/e-irsaliye-gecis-ve-zorunluluk-rehberi.html)
* 📄 [Temel Fatura ile Ticari Fatura Arasındaki Farklar ve 8 Günlük Ret Süresi](https://efaturabilgi.site/yazilar/temel-fatura-ticari-fatura-farklari-ve-itiraz.html)

---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Ticari ve kişisel projelerde serbestçe kullanılabilir.
