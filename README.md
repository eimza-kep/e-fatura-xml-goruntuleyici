# GİB UBL-TR e-Fatura & e-Arşiv XML Görüntüleyici 🧾🌐

[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Standart: GİB UBL-TR](https://img.shields.io/badge/Standart-G%C4%B0B%20UBL--TR%201.2-red.svg)](https://ebelge.gib.gov.tr)

Gelir İdaresi Başkanlığı (**GİB**) e-Belge portalından, özel entegratörlerden veya e-ticaret sitelerinden indirilen karmaşık `.xml` uzantılı **e-Fatura** ve **e-Arşiv Fatura** dosyalarını **kodlama bilmeden anında okunabilir hale getiren ve modern bir HTML faturasına dönüştüren** açık kaynaklı hafif araçtır.

---

## ✨ Neler Yapabilir?

* 📄 **UBL-TR 1.2 Desteği:** Standart GİB e-Fatura ve e-Arşiv XML yapısını doğrudan ayrıştırır.
* 🖥️ **Terminal Özeti:** Fatura No, Tarih, Satıcı/Alıcı VKN/TCKN, KDV ve Ödenecek Tutarı anında ekrana basar.
* 🌐 **Modern HTML Görseli (`--html`):** XML faturasını şık, profesyonel ve yazdırılabilir bir HTML e-Faturasına dönüştürür ve tarayıcınızda açar.
* 🤖 **JSON Çıkışı (`--json`):** Muhasebe programları, ERP sistemleri veya veritabanı aktarımları için JSON formatında veri üretir.

---

## 🚀 Hızlı Kullanım

### 1. Terminalde Hızlı Özet Görme
```bash
python ubl_viewer.py GIB2026000000001.xml
```

**Örnek Çıktı:**
```text
================================================================================
            GİB e-FATURA ÖZETİ: GIB2026000000001 (SATIS)
================================================================================
Tarih:        2026-09-18
Satıcı:       ABC TEKNOLOJİ YAZILIM A.Ş. (VKN/TCKN: 1234567890)
Alıcı:        XYZ LOJİSTİK VE TİCARET LTD. (VKN/TCKN: 9876543210)
--------------------------------------------------------------------------------
Mal/Hizmet:   15,000.00 TRY
Toplam KDV:   3,000.00 TRY
ÖDENECEK:     18,000.00 TRY
================================================================================
```

### 2. Tarayıcıda Görsel Fatura Olarak Açma
```bash
python ubl_viewer.py GIB2026000000001.xml --html
```
*XML dosyasının yanına `.html` dosyası üretilir ve varsayılan web tarayıcınızda açılır. Sayfa üzerinde doğrudan "Yazdır / PDF Olarak Kaydet" butonu yer alır.*

### 3. Özel Dosyaya Kaydetme ve Arka Plan Dönüşümü
```bash
# HTML olarak özel bir yola kaydetme (tarayıcı açmadan)
python ubl_viewer.py fatura.xml --output ./faturalar/fatura.html --no-browser

# JSON olarak dosyaya aktarma
python ubl_viewer.py fatura.xml --output fatura_verisi.json
```

### 4. JSON Formatında Çıktı Alma
```bash
python ubl_viewer.py GIB2026000000001.xml --json
```


---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında sunulmaktadır.


### 📚 İlgili Rehber ve Çözümler
* 📄 [GİB e-Arşiv Portaldan Fatura Kestikten Sonra İptal Süresi Kaç Gündür?](https://efatura-atolyesi.pages.dev/yazilar/gib-e-arsiv-fatura-iptal-suresi-kac-gun.html)
* 📄 [e-Fatura ile e-Arşiv Fatura Arasındaki Fark Nedir? Kime Hangisi Kesilir?](https://efatura-atolyesi.pages.dev/yazilar/e-fatura-ve-e-arsiv-arasindaki-farklar.html)
* 📄 [e-İrsaliyede Karekod (QR Kod) Olmaması Halinde Uygulanan Cezalar](https://efatura-atolyesi.pages.dev/yazilar/e-irsaliyede-karekod-zorunlulugu-ve-cezalar.html)
* 📄 [Yeni Kurulan Bir Şahıs Şirketi Hemen e-Faturaya Geçmek Zorunda mı?](https://edonusum-kobi.pages.dev/yazilar/yeni-kurulan-sahis-sirketi-e-fatura-zorunlu-mu.html)
