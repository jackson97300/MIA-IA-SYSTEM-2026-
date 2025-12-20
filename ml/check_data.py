import pandas as pd

df = pd.read_parquet('ml/data/labeled_trades.parquet')
df_test = df[df['date'].isin(['20251113', '20251114'])]

print(f'Total test: {len(df_test)}')
print(f'WINs: {(df_test["pnl_ticks"] > 0).sum()} ({(df_test["pnl_ticks"] > 0).mean()*100:.1f}%)')
print(f'LOSSes: {(df_test["pnl_ticks"] <= 0).sum()} ({(df_test["pnl_ticks"] <= 0).mean()*100:.1f}%)')
print(f'P&L moyen: {df_test["pnl_ticks"].mean():+.2f}t')
print(f'P&L median: {df_test["pnl_ticks"].median():+.2f}t')
print(f'P&L min: {df_test["pnl_ticks"].min():+.2f}t')
print(f'P&L max: {df_test["pnl_ticks"].max():+.2f}t')

# Echantillon de 10 trades
print('\nEchantillon (10 premiers trades):')
print(df_test[['date', 'pnl_ticks', 'win']].head(10).to_string())







