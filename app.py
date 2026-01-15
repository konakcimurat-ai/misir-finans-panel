import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Sayfa Yapılandırması
st.set_page_config(page_title="Mısır Tesis Finansal Kontrol Paneli (Şifreli)", layout="wide")

# ============================================================
# 🔒 ŞİFRELİ GİRİŞ (Streamlit Cloud Secrets)
# Streamlit Cloud → Manage app → Settings → Secrets içine ekle:
# APP_PASSWORD = "misir2026!"
# ============================================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("🔒 Erişim Korumalı Panel")
    st.caption("Bu panel sadece yetkilendirilmiş kişiler içindir.")

    # Secrets yoksa beyaz ekran yerine net mesaj
    app_pw = st.secrets.get("APP_PASSWORD", "")
    if not app_pw:
        st.error('APP_PASSWORD tanımlı değil. Manage app → Settings → Secrets içine ekleyin: APP_PASSWORD = "sifren"')
        st.stop()

    password = st.text_input("Şifre", type="password")

    if st.button("Giriş", use_container_width=True):
        if password == app_pw:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Hatalı şifre")

    return False


if not check_password():
    st.stop()

# --- SIDEBAR: PARAMETRELER ---
st.sidebar.header("⚙️ Finansal Parametreler")
usd_kur = st.sidebar.number_input("1 USD / EGP Kuru", min_value=1.0, value=48.50, step=0.1, key="usd_kur")
eur_kur = st.sidebar.number_input("1 EUR / EGP Kuru", min_value=1.0, value=52.80, step=0.1, key="eur_kur")

st.sidebar.divider()
st.sidebar.header("🏭 Operasyonel Ayarlar")
fire_orani = st.sidebar.slider("Fire Oranı (%)", 0, 30, 15, key="fire") / 100
kar_marji = st.sidebar.slider("Hedef Kâr Marjı (%)", 0, 100, 40, key="margin") / 100

# Bu slider BASE tablolarına dokunmaz, sadece senaryo OPEX çarpanı ekler
st.sidebar.caption("Not: Aşağıdaki ayar BASE rakamları değiştirmez, sadece senaryo hesabında çarpan uygular.")
opex_fire_esneklik = st.sidebar.slider("OPEX Fire Hassasiyeti (0 = kapalı)", 0.0, 1.0, 0.0, 0.05, key="opex_elastic")

# --- SABİTLER ---
amortisman_ayi = 12
vergi_orani = 0.225

# --- FONKSİYONLAR ---
def process_with_subtotals(items, kur, label):
    raw_df = pd.DataFrame(items, columns=["Kategori", "Kalem", "EGP", "USD", "Durum"])
    raw_df["Toplam (USD)"] = raw_df["USD"] + (raw_df["EGP"] / kur)
    raw_df["Toplam (EGP)"] = (raw_df["USD"] * kur) + raw_df["EGP"]

    final_list = []
    for cat in raw_df["Kategori"].unique():
        sub_df = raw_df[raw_df["Kategori"] == cat].copy()
        final_list.append(sub_df)
        subtotal = pd.DataFrame([{
            "Kategori": cat,
            "Kalem": f"--- {cat} ARA TOPLAM ---",
            "EGP": sub_df["EGP"].sum(),
            "USD": sub_df["USD"].sum(),
            "Toplam (USD)": sub_df["Toplam (USD)"].sum(),
            "Toplam (EGP)": sub_df["Toplam (EGP)"].sum(),
            "Durum": "ARA_TOPLAM"
        }])
        final_list.append(subtotal)

    grand_total = pd.DataFrame([{
        "Kategori": "FİNAL",
        "Kalem": f"🚀 TOPLAM {label}",
        "EGP": raw_df["EGP"].sum(),
        "USD": raw_df["USD"].sum(),
        "Toplam (USD)": raw_df["Toplam (USD)"].sum(),
        "Toplam (EGP)": raw_df["Toplam (EGP)"].sum(),
        "Durum": "GENEL_TOPLAM"
    }])
    final_list.append(grand_total)

    return pd.concat(final_list, ignore_index=True), raw_df


def apply_styles(row):
    if row["Durum"] == "ARA_TOPLAM":
        return ['background-color: #f8f9fa; font-weight: bold'] * len(row)
    if row["Durum"] == "GENEL_TOPLAM":
        return ['background-color: #2c3e50; color: white; font-weight: bold'] * len(row)
    return [''] * len(row)

# --- VERİ GİRİŞLERİ (SENİN RAKAMLARIN - DOKUNMADIM) ---
capex_items = [
    ("Gayrimenkul", "Kira Depozitosu (2 Aylık Güvence)", 530000, 0, "Kesin"),
    ("Gayrimenkul", "Peşin Kira (3 Aylık Ödeme)", 795000, 0, "Kesin"),
    ("Altyapı", "Elektrik Tesisat, Pano & Kablolama", 0, 3000, "Kesin"),
    ("Altyapı", "Mekanik Kurulum & Borulama", 0, 3000, "Tahmini"),
    ("Altyapı", "Su Tesisatı & Atık Su Bağlantıları", 0, 2000, "Tahmini"),
    ("Üretim", "Kompresör Sistemi (Ana Hat)", 77500, 0, "Kesin"),
    ("Üretim", "Vakum Fanları & Emiş Hattı", 242500, 0, "Tahmini"),
    ("Üretim", "Filtreleme Ünitesi & BiB Dolum", 0, 2000, "Tahmini"),
    ("Üretim", "Heater (Isıtıcı) Revizyonları", 0, 1500, "Tahmini"),
    ("Üretim", "Çuval Dikiş Makineleri", 7500, 0, "Kesin"),
    ("Lojistik", "Personel & Malzeme Kamyoneti", 1100000, 0, "Tahmini"),
    ("Lojistik", "Elektrikli/Dizel Forklift", 1000000, 0, "Tahmini"),
    ("Lojistik", "Zemin Kantarı", 16500, 0, "Kesin"),
    ("Lojistik", "Transpalet Seti", 21000, 0, "Kesin"),
    ("Sarf Malzeme", "Başlangıç Stok Çuval (1000 Adet)", 160000, 0, "Kesin"),
    ("Teknoloji", "ERP Yazılım, Server & Kamera Sis.", 400000, 0, "Tahmini"),
    ("Teknoloji", "Ofis PC, IP Tel & Yazıcı Seti", 168000, 0, "Tahmini"),
    ("İdari / Ofis", "Ofis Mobilya & Karşılama Seti", 23600, 0, "Kesin"),
    ("Personel", "Mutfak & Yemek Donanımı", 58700, 0, "Tahmini"),
    ("Rezerv", "Beklenmedik Durum Fonu", 478000, 1200, "Tahmini")
]

# --- HESAPLAMALAR (CAPEX) ---
styled_df_c, raw_df_c = process_with_subtotals(capex_items, usd_kur, "YATIRIM")
toplam_capex = raw_df_c["Toplam (USD)"].sum()
aylik_yatirim_odeme = toplam_capex / amortisman_ayi

# --- OPEX (SENİN RAKAMLARIN - DOKUNMADIM) ---
opex_items = [
    ("Hammadde", "Ham Tüy (Baz)", 0, 18585, "Tahmini"),
    ("Gayrimenkul", "Kira", 265000, 0, "Kesin"),
    ("Personel", "Müdür Net", 0, 700, "Kesin"),
    ("Personel", "Sigortalar & İşçi Maaş", 64800, 0, "Tahmini"),
    ("Personel", "Yemek & Yol", 20000, 0, "Tahmini"),
    ("Genel", "Hukuk/Muh/IT/Enerji", 103500 + (900 * eur_kur), 1200, "Kesin")
]
styled_df_o, raw_df_o = process_with_subtotals(opex_items, usd_kur, "İŞLETME")
aylik_sabit_opex_usd_base = raw_df_o["Toplam (USD)"].sum()

# --- 12 AY PNL MOTORU ---
# BASE: senin verdiğin gibi (dokunmadım)
# SENARYO: sidebar fire + kar_marji + opex_fire_esneklik ile çarpan
pnl_base = []
pnl_scn = []
kasa_base = 0.0
kasa_scn = 0.0

for ay in range(1, 13):
    v_sayisi = 2 if ay >= 8 else 1
    kap_orani = 0 if ay == 1 else (0.5 if ay == 2 else 1.0)
    if ay >= 8:
        kap_orani = 2.0

    # BASE
    gelir_b = 95000 if ay == 5 else (48150 * v_sayisi if ay > 5 else 0)
    ham_b = 18585 * kap_orani
    op_b = 12450 if v_sayisi == 1 else 21500

    net_b = gelir_b - ham_b - op_b - aylik_yatirim_odeme
    kasa_base += net_b
    pnl_base.append({
        "Ay": f"Ay {ay}",
        "Gelir ($)": gelir_b,
        "Hammadde ($)": ham_b,
        "OPEX ($)": op_b,
        "Yatırım ($)": aylik_yatirim_odeme,
        "Aylık Net ($)": net_b,
        "Kasa ($)": kasa_base
    })

    # SENARYO (BASE'e dokunmadan çarpan)
    gelir_s = gelir_b * (1 + kar_marji)  # fiyat / marj etkisi
    fire_katsayi = 1 / max((1 - fire_orani), 0.01)  # fire arttıkça ham maliyet artar
    ham_s = ham_b * fire_katsayi
    op_s = op_b * (1 + opex_fire_esneklik * fire_orani)

    net_s = gelir_s - ham_s - op_s - aylik_yatirim_odeme
    kasa_scn += net_s
    pnl_scn.append({
        "Ay": f"Ay {ay}",
        "Gelir ($)": gelir_s,
        "Hammadde ($)": ham_s,
        "OPEX ($)": op_s,
        "Yatırım ($)": aylik_yatirim_odeme,
        "Aylık Net ($)": net_s,
        "Kasa ($)": kasa_scn
    })

df_pnl_base = pd.DataFrame(pnl_base)
df_pnl_scn = pd.DataFrame(pnl_scn)

# --- UI ---
st.title("🏭 Mısır Tesis Finansal Kontrol Paneli")
st.markdown("---")

t1, t2, t3, t4, t5 = st.tabs(["📊 Yatırım (CAPEX)", "💸 İşletme (OPEX)", "📈 Maliyet Analizi", "💰 Nakit Akışı", "🏆 Kârlılık Raporu"])

# TAB 1: CAPEX
with t1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("TOPLAM CAPEX", f"{toplam_capex:,.0f} $")
        st.plotly_chart(px.pie(raw_df_c, values='Toplam (USD)', names='Kategori', title="Yatırım Kırılımı"), use_container_width=True)
    with col2:
        st.dataframe(
            styled_df_c.style.apply(apply_styles, axis=1).format({"EGP": "{:,.0f}", "USD": "{:,.0f}", "Toplam (USD)": "{:,.2f} $"}),
            use_container_width=True,
            hide_index=True
        )

# TAB 2: OPEX
with t2:
    st.plotly_chart(px.bar(raw_df_o, x='Kategori', y='Toplam (USD)', color='Kategori', title="Aylık Sabit Gider Dağılımı"), use_container_width=True)
    st.dataframe(
        styled_df_o.style.apply(apply_styles, axis=1).format({"EGP": "{:,.0f}", "USD": "{:,.0f}", "Toplam (USD)": "{:,.2f} $"}),
        use_container_width=True,
        hide_index=True
    )

# TAB 3: Maliyet analizi (sidebar etkili)
with t3:
    op_birim = (12450 + aylik_yatirim_odeme) / ((17600) * (1 - fire_orani))
    res_maliyet = []
    for u in [{"Ürün": "Moulard", "Ham": 1.30}, {"Ürün": "Barbary", "Ham": 1.10}, {"Ürün": "French Duck", "Ham": 0.80}]:
        fm = u["Ham"] / (1 - fire_orani)
        tot = fm + op_birim
        res_maliyet.append({"Ürün": u["Ürün"], "Maliyet ($)": tot, "Satış ($)": tot * (1 + kar_marji)})
    df_m = pd.DataFrame(res_maliyet)

    st.plotly_chart(px.bar(df_m, x="Ürün", y=["Maliyet ($)", "Satış ($)"], barmode="group", title="Ürün Başı Kâr Marjı Analizi"), use_container_width=True)
    st.table(df_m.style.format({"Maliyet ($)": "{:.2f} $", "Satış ($)": "{:.2f} $"}))

# TAB 4: Nakit akışı (BASE vs SENARYO birlikte)
with t4:
    fig_nakit = go.Figure()
    fig_nakit.add_trace(go.Scatter(x=df_pnl_base["Ay"], y=df_pnl_base["Kasa ($)"], mode='lines+markers', name="Kümülatif Kasa (BASE)"))
    fig_nakit.add_trace(go.Scatter(x=df_pnl_scn["Ay"], y=df_pnl_scn["Kasa ($)"], mode='lines+markers', name="Kümülatif Kasa (SENARYO)"))
    fig_nakit.add_hline(y=0, line_dash="dash", line_color="red")
    fig_nakit.update_layout(title="Kümülatif Kasa (BASE vs SENARYO)")
    st.plotly_chart(fig_nakit, use_container_width=True)

    df_show = df_pnl_base.merge(df_pnl_scn, on="Ay", suffixes=(" (BASE)", " (SENARYO)"))
    money_cols = [c for c in df_show.columns if "$" in c]
    st.dataframe(df_show.style.format({c: "{:,.0f} $" for c in money_cols}), use_container_width=True, hide_index=True)

# TAB 5: Kârlılık (BASE vs SENARYO)
with t5:
    ebt_base = df_pnl_base["Aylık Net ($)"].sum()
    vergi_base = ebt_base * vergi_orani if ebt_base > 0 else 0
    net_base = ebt_base - vergi_base

    ebt_scn = df_pnl_scn["Aylık Net ($)"].sum()
    vergi_scn = ebt_scn * vergi_orani if ebt_scn > 0 else 0
    net_scn = ebt_scn - vergi_scn

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net Yıllık Kâr (BASE)", f"{net_base:,.0f} $")
    c2.metric("Net Yıllık Kâr (SENARYO)", f"{net_scn:,.0f} $", delta=f"{(net_scn-net_base):+,.0f} $")
    c3.metric("Vergi (BASE)", f"{vergi_base:,.0f} $")
    c4.metric("Vergi (SENARYO)", f"{vergi_scn:,.0f} $")

    st.plotly_chart(
        go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "relative", "relative", "total"],
            x=["Satışlar", "Hammadde", "OPEX", "Yatırım Geri Ödeme", "NET KÂR (SENARYO)"],
            y=[
                df_pnl_scn["Gelir ($)"].sum(),
                -df_pnl_scn["Hammadde ($)"].sum(),
                -df_pnl_scn["OPEX ($)"].sum(),
                -df_pnl_scn["Yatırım ($)"].sum(),
                0
            ]
        )).update_layout(title="Yıllık Finansal Akış Özeti (Waterfall) - SENARYO"),
        use_container_width=True
    )
