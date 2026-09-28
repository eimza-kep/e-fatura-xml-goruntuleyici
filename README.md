# GİB UBL-TR e-Fatura, e-Arşiv & e-İrsaliye XML Görüntüleyici 🧾✨

[![Python CI](https://github.com/eimza-kep/e-fatura-xml-goruntuleyici/actions/workflows/ci.yml/badge.svg)](https://github.com/eimza-kep/e-fatura-xml-goruntuleyici/actions)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Standart: UBL-TR 1.2](https://img.shields.io/badge/Standart-UBL--TR%201.2-red.svg)](https://ebelge.gib.gov.tr)
[![Blog](https://img.shields.io/badge/Rehber-e--Fatura%20At%C3%B6lyesi-emerald.svg)](https://efaturabilgi.site/)

Gelir İdaresi Başkanlığı (GİB) **UBL-TR 1.2 standardındaki e-Fatura, e-Arşiv ve e-İrsaliye (DespatchAdvice)** XML dosyalarını ayrıştırıp; fatura kalemlerini, satıcı/alıcı/taşıyıcı bilgilerini ve KDV dağılımını terminalde özetleyen, muhasebe CSV'sine aktaran ve tarayıcıda yazdırılabilir modern bir HTML faturası oluşturan açık kaynaklı Python aracıdır.

---

## ✨ Öne Çıkan Özellikler

* ⚡ **Sıfır Bağımlılık (Zero-Dependency):** Ek kütüphane veya Java kurulumu gerekmez. Saf Python ile çalışır.
* 📦 **Çoklu Belge Desteği:** e-Fatura, e-Arşiv Fatura ve **e-İrsaliye (DespatchAdvice)** belgelerini otomatik tanır.
* 🚚 **Lojistik ve Taşıyıcı Bilgileri:** e-İrsaliyelerdeki plaka, taşıyıcı firma ve sevk kalemlerini ayrıştırır.
* 🖨️ **Baskıya Hazır HTML:** Tailwind CSS destekli, yazdırma moduna özel (`@media print`) şık tasarım.
* 📊 **CSV Dışa Aktarım:** Fatura kalemlerini Excel ve muhasebe programlarına aktarılabilir CSV formatına döker.
* 📁 **Toplu Dizin Tarama:** `--dir` ile bir klasördeki yüzlerce e-belgeyi tek komutla tarayıp listeleyebilir.

---

## 🚀 Hızlı Başlangıç

### 1. Terminalde Belge Özeti Görüntüleme
```bash
python ubl_viewer.py fatura.xml
```

### 2. Tarayıcıda Açılabilir HTML Faturası Üretme
```bash
python ubl_viewer.py fatura.xml --html
```

### 3. Fatura Kalemlerini CSV'ye Aktarma
```bash
python ubl_viewer.py fatura.xml --csv
```

### 4. Klasördeki Belgeleri Toplu İnceleme
```bash
python ubl_viewer.py --dir ./gelen_faturalar/ --csv toplu_ozet.csv
```

---

## 🐍 Python Projelerinde Kullanım

```python
from ubl_viewer import parse_ubl_document, generate_html_invoice

# XML belgesini ayrıştır
fatura = parse_ubl_document("fatura.xml")

print(f"Tür: {fatura['belge_turu']} | Fatura No: {fatura['fatura_no']}")
print(f"Ödenecek Tutar: {fatura['tutarlar']['odenecek_tutar']:,.2f} {fatura['para_birimi']}")

# HTML üret
generate_html_invoice(fatura, "goruntu.html")
```

---

## 🔗 E-Dönüşüm Açık Kaynak Ekosistemi

Bu araç [eimza-kep](https://github.com/eimza-kep) organizasyonunun açık kaynak e-dönüşüm araçları ekosisteminin bir parçasıdır:

* 🇹🇷 **[awesome-turkiye-e-donusum](https://github.com/eimza-kep/awesome-turkiye-e-donusum):** Türkiye E-Dönüşüm kütüphane, mevzuat ve araçlar listesi.
* 📊 **[gib-edefter-berat-xml-dogrulayici](https://github.com/eimza-kep/gib-edefter-berat-xml-dogrulayici):** e-Defter ve Berat XML dosyalarını şema ve bakiye doğrulama aracı.
* 📑 **[e-fatura-itiraz-ve-iade-scripti](https://github.com/eimza-kep/e-fatura-itiraz-ve-iade-scripti):** 8 günlük yasal itiraz süresi takip ve fatura iade tutanağı scripti.
* 📬 **[kep-adresi-dogrulayici](https://github.com/eimza-kep/kep-adresi-dogrulayici):** KEP adresi ve BTK operatör denetleyici.

---

## 📚 İlgili Teknik Rehberler
* 📄 [e-Fatura ve e-Arşiv Fatura Arasındaki Temel Hukuki ve Teknik Farklar](https://efaturabilgi.site/yazilar/e-fatura-ve-e-arsiv-arasindaki-farklar.html)
* 📄 [e-İrsaliye Zorunluluğu ve Sevk Sürecinde Karekod Uygulaması](https://edonusumkobi.site/yazilar/e-irsaliye-gecis-ve-zorunluluk-rehberi.html)
* 📄 [Temel Fatura ile Ticari Fatura Arasındaki Farklar ve 8 Günlük Ret Süresi](https://efaturabilgi.site/yazilar/temel-fatura-ticari-fatura-farklari-ve-itiraz.html)

---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.
