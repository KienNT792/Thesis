"""Generate the analysis notebooks (so cell sources stay reviewable in git)."""
import nbformat as nbf
from pathlib import Path

HERE = Path(__file__).resolve().parent


def nb(cells):
    n = nbf.v4.new_notebook()
    n.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1]) for c in cells]
    n.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    return n


SETUP = """import sys, warnings
sys.path.insert(0, '.')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from _common import *
plt.rcParams.update({'figure.dpi': 100, 'axes.grid': True, 'grid.alpha': .3})
news, px, tg = load()
vn30 = px[px.ticker == 'VN30'].set_index('date').sort_index()
print(f'news {len(news):,} | price rows {len(px):,} | targets {len(tg):,}')"""

nb1 = nb([
("md", "# 01 · Chất lượng dữ liệu và đặc điểm\nMục tiêu: đo xem dữ liệu hiện có cho phép mô hình nào. Mọi số liệu được tính lại khi chạy notebook."),
("code", SETUP),
("md", "## 1. Mật độ tin theo phiên (thị trường)"),
("code", """per = news.dropna(subset=['session_date']).groupby('session_date').size()
fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
per.rolling(20).mean().plot(ax=ax[0]); ax[0].axhline(20, color='r', ls='--', label='ngưỡng G1 = 20'); ax[0].set_title('Số bài/phiên (TB 20 phiên)'); ax[0].legend()
news.groupby([news.session_date.dt.year, 'source']).size().unstack(fill_value=0).plot.bar(stacked=True, ax=ax[1]); ax[1].set_title('Bài theo năm và nguồn')
savefig(fig, 'nb01_news_density'); plt.show()
print(per.groupby(per.index.year).agg(['median', 'min', 'max']))"""),
("md", "## 2. Thời điểm đăng bài và quy tắc phiên (look-ahead)"),
("code", """hr = news.published_at_ict.str[11:13].astype(int)
after = (news.published_at_ict.str[11:19] > '15:00:00').mean()
fig, ax = plt.subplots(figsize=(8, 3.5)); hr.value_counts().sort_index().plot.bar(ax=ax); ax.axvline(15, color='r'); ax.set_title('Giờ đăng (ICT)')
savefig(fig, 'nb01_hour'); plt.show()
print(f'Bài đăng sau 15:00 ICT: {after:.1%} (gán sang phiên kế tiếp); trước đó đăng sau 15:00 ICT (gán sang phiên kế tiếp); placeholder: {news.placeholder_ts.mean():.4%}')"""),
("md", "## 3. Tin theo mã (độ thưa)"),
("code", """import re
tick = sorted(px[px.in_vn30].ticker.unique())
pat = {t: re.compile(rf'\\b{t}\\b') for t in tick}
txt = news[['session_date', 'title']].dropna()
days = txt.session_date.nunique()
cov = {t: txt[txt.title.str.contains(pat[t])].session_date.nunique() / days for t in tick}
cov = pd.Series(cov).sort_values()
fig, ax = plt.subplots(figsize=(11, 4)); cov.plot.bar(ax=ax); ax.set_title('Tỷ lệ phiên có >=1 bài nhắc mã (tiêu đề)')
savefig(fig, 'nb01_ticker_cov'); plt.show()
print(f'trung vị {cov.median():.1%}; số mã <10% phiên: {(cov<.10).sum()}/{len(cov)}; >50%: {(cov>.5).sum()}')"""),
("md", "## 4. Giá: phủ và chế độ biến động"),
("code", """vol = np.log(vn30.close).diff().rolling(20).std() * np.sqrt(252)
fig, ax = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
vn30.close.plot(ax=ax[0]); ax[0].set_title('VN30')
vol.plot(ax=ax[1]); ax[1].set_title('Biến động thực hiện 20 phiên (annualised)')
savefig(fig, 'nb01_regimes'); plt.show()
yr = np.log(vn30.close).diff().groupby(vn30.index.year).agg(['mean', 'std', 'count'])
yr['mean_ann'] = yr['mean'] * 252; yr['vol_ann'] = yr['std'] * np.sqrt(252)
print(yr[['mean_ann', 'vol_ann', 'count']].round(3))"""),
("code", """cal = px[px.ticker=='VNINDEX'].date.nunique()
c = px[px.in_vn30].groupby('ticker').date.nunique()
member_days = px.groupby('date').in_vn30.sum()
print('ngày VNINDEX:', cal, '| ngày có đủ 30 thành viên có giá:', int((member_days==30).sum()), '| ngày 29 thành viên:', int((member_days==29).sum()))"""),
("md", "## Kết luận từ notebook 01 (đọc cùng số liệu ở trên)\n- Tin mức thị trường dày và đều; tin theo mã thưa, nên chỉ số sợ hãi thị trường là tín hiệu chính.\n- Biến động thay đổi mạnh giữa các năm (chế độ thị trường), nên mô hình phải được kiểm tra qua walk-forward chứ không dựa vào một lần chia.\n- Thành viên VN30 có giá đủ 30 mã trừ khoảng ROS."),
])

nb2 = nb([
("md", "# 02 · Nhãn, mẫu hiệu dụng và sức mạnh kiểm định\nCâu hỏi: với ~1.700 phiên và nhãn 5 phiên chồng lấn, loại mô hình nào chứng minh được là có thể?"),
("code", SETUP),
("md", "## 1. Cân bằng nhãn"),
("code", """tg['year'] = tg.date.dt.year
print(tg.groupby('year')[['y_up', 'y_drop']].mean().round(3).assign(n=tg.groupby('year').size()))
print('tổng:', tg[['y_up', 'y_drop']].mean().round(3).to_dict())"""),
("md", "## 2. Tự tương quan: chồng lấn làm giảm cỡ mẫu"),
("code", """from statsmodels.tsa.stattools import acf
r1 = np.log(vn30.close).diff().dropna()
f5 = tg.set_index('date').fwd_ret
a1, a5 = acf(r1, nlags=10), acf(f5, nlags=10)
fig, ax = plt.subplots(1, 2, figsize=(12, 3.5))
ax[0].bar(range(11), a1); ax[0].set_title('ACF lợi suất 1 phiên'); ax[1].bar(range(11), a5); ax[1].set_title('ACF lợi suất 5 phiên chồng lấn')
for a in ax: a.axhline(1.96/np.sqrt(len(r1)), color='r', ls='--'); a.axhline(-1.96/np.sqrt(len(r1)), color='r', ls='--')
savefig(fig, 'nb02_acf'); plt.show()
# Cỡ mẫu hiệu dụng cho nhãn chồng lấn: n / (1 + 2*sum Bartlett*rho_k) với K=4
K = 4; rho = acf(f5, nlags=K)[1:]; w = 1 - np.arange(1, K + 1) / (K + 1)
n = len(f5); inflation = 1 + 2 * np.sum(w * rho)
print(f'n={n}, hệ số phồng phương sai={inflation:.2f}, n_eff≈{n/inflation:.0f}; cửa sổ không chồng lấn={n//5}')
for col in ['y_up', 'y_drop']:
    ac = acf(tg[col], nlags=6)[1:]; print(col, 'ACF lag1..5:', ac[:5].round(2))"""),
("md", "## 3. Sức mạnh kiểm định: tương quan nhỏ nhất phát hiện được"),
("code", """from scipy import stats
def min_detectable_r(n_eff, alpha=.05, power=.8, one_sided=True):
    za = stats.norm.ppf(1 - alpha / (1 if one_sided else 2)); zb = stats.norm.ppf(power)
    return np.tanh((za + zb) / np.sqrt(n_eff - 3))
rows = []
for label, ne in [('mẫu độc lập 5 phiên (~%d)' % (n//5), n//5), ('n_eff (hiệu chỉnh ACF)', int(n/inflation)), ('hậu mốc LLM: 2026 (~34)', 34)]:
    rows.append((label, ne, min_detectable_r(ne)))
pw = pd.DataFrame(rows, columns=['tình huống', 'n_eff', 'r_min (80% power, 1 phía, α=5%)']); print(pw.round(3).to_string(index=False))
ns = np.arange(30, 1800, 10); fig, ax = plt.subplots(figsize=(7, 3.5))
ax.plot(ns, [min_detectable_r(x) for x in ns]); ax.set_xlabel('n hiệu dụng'); ax.set_ylabel('r tối thiểu'); ax.set_title('Hiệu ứng nhỏ nhất phát hiện được')
savefig(fig, 'nb02_power'); plt.show()"""),
("md", "## 4. Tính dừng/chế độ"),
("code", """from statsmodels.tsa.stattools import adfuller
print('ADF p (lợi suất 1 phiên):', round(adfuller(r1)[1], 4))
vol_y = r1.groupby(r1.index.year).std() * np.sqrt(252)
fig, ax = plt.subplots(figsize=(7, 3)); vol_y.plot.bar(ax=ax); ax.set_title('Biến động annualised theo năm')
savefig(fig, 'nb02_vol_year'); plt.show()
print('Tỷ lệ biến động lớn nhất/nhỏ nhất theo năm:', round(vol_y.max() / vol_y.min(), 2))"""),
("md", "## Kết luận từ notebook 02\n- Lợi suất 5 phiên chồng lấn có tự tương quan lớn, nên n hiệu dụng gần số cửa sổ không chồng lấn, không phải 1.700.\n- Hiệu ứng nhỏ nhất phát hiện được (r_min) cao với n hiệu dụng này; chỉ những tín hiệu khá rõ mới kiểm định được.\n- Mô hình nhiều tham số (mạng nơ-ron) sẽ khớp quá mức trên cỡ mẫu này; ưu tiên mô hình ít tham số, có kiểm soát."),
])

nb3 = nb([
("md", "# 03 · So sánh mô hình bằng purged walk-forward\nĐặc trưng tin tức ở đây là **proxy thô** (khối lượng và tỷ lệ từ khóa tiêu cực) để thử cơ chế; không phải chỉ số sợ hãi LLM. Mục đích: chọn *họ mô hình* dựa trên dữ liệu, không kết luận về sức mạnh dự báo của tin tức."),
("code", SETUP + """
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss
import lightgbm as lgb
import statsmodels.api as sm"""),
("code", """pf = price_features(px); nf = news_daily_features(news)
nf = nf.reindex(pf.index).fillna(0)
nf['ln_n'] = np.log1p(nf.n_all); nf['ln_mkt'] = np.log1p(nf.n_market)
nf['ln_n_z'] = (nf.ln_n - nf.ln_n.rolling(60).mean()) / nf.ln_n.rolling(60).std()
nf['neg_z'] = (nf.neg_rate - nf.neg_rate.rolling(60).mean()) / nf.neg_rate.rolling(60).std()
nf['neg_5d'] = nf.neg_rate.rolling(5).mean()
PRICE = ['ret1', 'ret5', 'ret20', 'vol20', 'vol5_over_20', 'volu_z', 'dd60']
NEWS = ['ln_n_z', 'neg_z', 'neg_5d', 'after_hours']
D = tg.set_index('date').join(pf).join(nf[NEWS]).dropna(subset=PRICE + NEWS + ['y_up'])
print(D.shape, D.index.min().date(), D.index.max().date())"""),
("code", """def folds(D, first_train=750, test_len=63, embargo=5):
    idx = D.index; t_end = D.t_end
    i = first_train
    while i < len(idx):
        test = idx[i:i + test_len]
        t0 = test[0]
        # purge: loại mẫu huấn luyện có cửa sổ nhãn chạm vào/trùng test; thêm embargo
        train = idx[:i - embargo]
        train = train[t_end.loc[train].values < np.datetime64(t0)]
        yield train, test
        i += test_len

def make(name):
    if name == 'logit_price':   return PRICE, make_pipeline(StandardScaler(), LogisticRegression(C=.1, max_iter=500)), 'lin'
    if name == 'enet_price_news': return PRICE + NEWS, make_pipeline(StandardScaler(), LogisticRegression(penalty='elasticnet', solver='saga', l1_ratio=.5, C=.1, max_iter=3000)), 'lin'
    if name == 'lgbm':          return PRICE + NEWS, lgb.LGBMClassifier(n_estimators=150, max_depth=2, num_leaves=4, learning_rate=.03, subsample=.8, subsample_freq=1, colsample_bytree=.8, min_child_samples=40, reg_lambda=5, verbose=-1, random_state=0), 'tree'
    if name == 'mlp':           return PRICE + NEWS, make_pipeline(StandardScaler(), MLPClassifier((32, 16), alpha=1e-2, max_iter=600, early_stopping=False, random_state=0)), 'nn'

MODELS = ['logit_price', 'enet_price_news', 'lgbm', 'mlp']
def run(target):
    out = {m: [] for m in MODELS}; base = []; dates = []
    for tr, te in folds(D):
        ytr, yte = D.loc[tr, target].values, D.loc[te, target].values
        base.append(np.full(len(te), ytr.mean())); dates.append(te)
        for m in MODELS:
            cols, mod, _ = make(m)
            mod.fit(D.loc[tr, cols].values, ytr)
            out[m].append(mod.predict_proba(D.loc[te, cols].values)[:, 1])
    idx = np.concatenate([d.values for d in dates])
    P = pd.DataFrame({m: np.concatenate(v) for m, v in out.items()}, index=idx); P['base'] = np.concatenate(base)
    P['y'] = D.loc[idx, target].values
    return P

res = {t: run(t) for t in ['y_drop', 'y_up']}
print({t: len(P) for t, P in res.items()}, 'quan sát OOS')"""),
("md", "## 1. Chỉ số ngoài mẫu"),
("code", """def table(P):
    rows = []
    for m in MODELS + ['base']:
        p = P[m].values; y = P.y.values
        bs = brier_score_loss(y, p); bs0 = brier_score_loss(y, P.base.values)
        auc = roc_auc_score(y, p) if m != 'base' else .5
        thr = np.quantile(p, 1 - y.mean()) if m != 'base' else 1.1
        rows.append((m, bs, 1 - bs / bs0, auc, mcc(y, (p >= thr).astype(int))))
    return pd.DataFrame(rows, columns=['model', 'Brier', 'BSS vs base', 'AUC', 'MCC']).set_index('model').round(4)
for t, P in res.items():
    print('==', t, '(prevalence OOS = %.3f)' % P.y.mean()); print(table(P))"""),
("md", "## 2. Kiểm định thống kê (HAC cho chồng lấn 5 phiên)"),
("code", """def cw_prob(P, small, big, lags=4):
    y = P.y.values; p0 = P[small].values; p1 = P[big].values
    f = (y - p0) ** 2 - ((y - p1) ** 2 - (p0 - p1) ** 2)  # Clark-West adj (cho mô hình lồng nhau)
    m = sm.OLS(f, np.ones_like(f)).fit(cov_type='HAC', cov_kwds={'maxlags': lags})
    return m.params[0], m.tvalues[0], stats.norm.sf(m.tvalues[0])

def dm_prob(P, a, b, lags=4):
    y = P.y.values; d = (y - P[a].values) ** 2 - (y - P[b].values) ** 2
    m = sm.OLS(d, np.ones_like(d)).fit(cov_type='HAC', cov_kwds={'maxlags': lags})
    return m.params[0], m.tvalues[0], 2 * stats.norm.sf(abs(m.tvalues[0]))

from scipy import stats
rows = []
for t, P in res.items():
    rows.append((t, 'CW: logit_price ⊂ enet_price_news', *cw_prob(P, 'logit_price', 'enet_price_news')))
    rows.append((t, 'CW: base vs logit_price', *cw_prob(P.assign(b0=P.base), 'b0', 'logit_price')))
    rows.append((t, 'DM: enet_price_news vs lgbm', *dm_prob(P, 'enet_price_news', 'lgbm')))
    rows.append((t, 'DM: enet_price_news vs mlp', *dm_prob(P, 'enet_price_news', 'mlp')))
print(pd.DataFrame(rows, columns=['target', 'test', 'mean_stat', 't_HAC', 'p']).round(4).to_string(index=False))"""),
("md", "## 2b. Công bằng với mạng nơ-ron: MLP điều hòa mạnh\nMLP ở trên chưa tinh chỉnh. Thử cấu hình nhỏ và alpha lớn để loại trừ khả năng kết quả xấu chỉ do cấu hình."),
("code", """def run_mlp(target, hidden, alpha):
    ps, ys, ix = [], [], []
    for tr, te in folds(D):
        cols = PRICE + NEWS
        mod = make_pipeline(StandardScaler(), MLPClassifier(hidden, alpha=alpha, max_iter=800, early_stopping=True, validation_fraction=.2, n_iter_no_change=15, random_state=0))
        mod.fit(D.loc[tr, cols].values, D.loc[tr, target].values)
        ps.append(mod.predict_proba(D.loc[te, cols].values)[:, 1]); ix.append(te.values)
    return np.concatenate(ix), np.concatenate(ps)
rows = []
for t in ['y_drop', 'y_up']:
    P = res[t]
    for hidden, alpha in [((32, 16), 1e-2), ((8,), 1.0), ((4,), 10.0)]:
        ix, p = run_mlp(t, hidden, alpha)
        y = P.loc[ix, 'y'].values; b = P.loc[ix, 'base'].values
        rows.append((t, str(hidden), alpha, round(1 - brier_score_loss(y, p) / brier_score_loss(y, b), 4), round(roc_auc_score(y, p), 3), round(p.std(), 3)))
print(pd.DataFrame(rows, columns=['target', 'hidden', 'alpha', 'BSS vs base', 'AUC', 'std(p̂)']).to_string(index=False))"""),
("md", "## 3. Ổn định theo thời gian và độ lệch của từng họ mô hình"),
("code", """fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
for ax, (t, P) in zip(axes, res.items()):
    for m in MODELS:
        d = (P.y - P.base) ** 2 - (P.y - P[m]) ** 2
        d.cumsum().plot(ax=ax, label=m)
    ax.axhline(0, color='k', lw=.8); ax.set_title(f'Lợi ích Brier tích lũy so với baseline ({t})'); ax.legend(fontsize=8)
savefig(fig, 'nb03_cum_brier'); plt.show()
yearly = []
for t, P in res.items():
    for y_, g in P.groupby(pd.DatetimeIndex(P.index).year):
        row = {'target': t, 'year': y_, 'n': len(g)}
        for m in MODELS: row[m] = round(1 - brier_score_loss(g.y, g[m]) / brier_score_loss(g.y, g.base), 3)
        yearly.append(row)
print('BSS theo năm (OOS):'); print(pd.DataFrame(yearly).to_string(index=False))"""),
("code", """# Độ nhạy phương sai: spread xác suất dự báo cho từng họ mô hình
print(pd.DataFrame({t: P[MODELS].std() for t, P in res.items()}).round(3).rename_axis('std(p̂)'))
fig, ax = plt.subplots(figsize=(7, 3.5))
for m in MODELS: ax.hist(res['y_drop'][m], bins=30, alpha=.4, label=m)
ax.set_title('Phân phối xác suất dự báo (y_drop)'); ax.legend(); savefig(fig, 'nb03_prob_dist'); plt.show()"""),
("code", """n_oos = len(res['y_drop']); infl = 3.48
def min_detectable_r(n_eff, alpha=.05, power=.8):
    return np.tanh((stats.norm.ppf(1 - alpha) + stats.norm.ppf(power)) / np.sqrt(n_eff - 3))
print(f'OOS = {n_oos} phiên (~{n_oos/5:.0f} cửa sổ độc lập, n_eff~{n_oos/infl:.0f}); r_min (80% power) ≈ {min_detectable_r(int(n_oos/infl)):.2f}')"""),
("md", "## Kết luận từ notebook 03\n- Không mô hình nào có lợi ích ngoài mẫu đáng kể so với baseline; điều này được kỳ vọng vì chỉ dùng đặc trưng giá và proxy tin rất thô, và vì OOS chỉ có vài trăm quan sát hiệu dụng (sức mạnh thấp).\n- Điều phân biệt các *họ mô hình* là độ ổn định, không phải độ chính xác: logistic điều hòa gần baseline; cây nông lệch nhẹ; MLP quá tự tin (std p̂ lớn), tệ hơn rõ rệt, và vẫn kém ngay cả khi điều hòa mạnh (xem 2b).\n- Do đó proxy tin tức ở đây không được diễn giải là bằng chứng về sức mạnh dự báo của chỉ số sợ hãi LLM."),
])
for name, n in [("01_data_quality_eda", nb1), ("02_target_sample_power", nb2), ("03_model_comparison", nb3)]:
    nbf.write(n, HERE / f"{name}.ipynb")
print('written')
