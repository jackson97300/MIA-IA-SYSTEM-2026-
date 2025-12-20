"""
Test du module Prop Firm
Exécuter: python -m src.prop_firm.test_prop_firm
"""
from datetime import datetime
import sys

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Ajouter le répertoire parent au path
sys.path.insert(0, r'D:\MIA_IA_system')

from src.prop_firm import (
    PropFirmManager,
    Trade,
    TradeDirection,
    get_prop_firm_config,
    get_account_config,
    get_contract_spec,
    calculate_pnl_from_ticks,
)


def test_contract_specs():
    """Test des spécifications de contrats"""
    print("\n" + "="*60)
    print("📊 TEST: Contract Specifications")
    print("="*60)

    for symbol in ["ES", "MES", "NQ", "MNQ", "RTY", "M2K"]:
        spec = get_contract_spec(symbol)
        print(f"  {symbol}: tick_size={spec.tick_size}, tick_value=${spec.tick_value}, is_micro={spec.is_micro}")

    # Test PnL calculation
    pnl = calculate_pnl_from_ticks("ES", 10, 1)
    print(f"\n  10 ticks ES (1 contrat) = ${pnl:.2f}")

    pnl = calculate_pnl_from_ticks("MES", 10, 5)
    print(f"  10 ticks MES (5 contrats) = ${pnl:.2f}")

    print("  ✅ Contract specs OK!")


def test_prop_firm_config():
    """Test des configurations prop firm"""
    print("\n" + "="*60)
    print("🏢 TEST: Prop Firm Configurations")
    print("="*60)

    for prop_firm in ["APEX", "TOPSTEP", "PHIDIAS"]:
        config = get_prop_firm_config(prop_firm)
        print(f"\n  {prop_firm}:")
        print(f"    - DD Type: {config['drawdown_type'].value}")
        print(f"    - Min Days: {config['min_trading_days']}")
        print(f"    - Consistency: {config['consistency_rule']}")

        accounts = list(config['accounts'].keys())
        print(f"    - Accounts: {accounts}")

    # Test account config
    apex_50k = get_account_config("APEX", "50K")
    print(f"\n  APEX 50K:")
    print(f"    - Starting: ${apex_50k['starting_balance']:,}")
    print(f"    - Target: ${apex_50k['profit_target']:,}")
    print(f"    - Trailing DD: ${apex_50k['trailing_dd']:,}")
    print(f"    - Max Contracts: {apex_50k['max_contracts']}")

    print("  ✅ Prop firm config OK!")


def test_position_sizer():
    """Test du position sizer"""
    print("\n" + "="*60)
    print("📐 TEST: Position Sizer")
    print("="*60)

    manager = PropFirmManager(
        prop_firm="APEX",
        account_size="50K",
        mode="EVALUATION"
    )

    # Test sizing
    size = manager.calculate_position("MES", stop_loss_ticks=12)
    print(f"\n  MES avec SL 12 ticks:")
    print(f"    - Contracts: {size.contracts}")
    print(f"    - Total Risk: ${size.total_risk:.2f}")
    print(f"    - Risk % DD: {size.risk_percent_of_dd:.2f}%")
    print(f"    - Recommendation: {size.recommendation}")
    if size.warnings:
        print(f"    - Warnings: {size.warnings}")

    # Test sizing table
    table = manager.position_sizer.get_sizing_table("MES", [8, 10, 12, 15, 20])
    print(f"\n  Sizing Table MES:")
    print(f"    Available DD: ${table['available_dd']:,.2f}")
    print(f"    Max Risk: ${table['max_risk']:,.2f}")
    for sl, data in table['sizes'].items():
        print(f"    SL {sl}t: {data['contracts']} contracts (${data['total_risk']:.2f}, {data['risk_percent']:.1f}%)")

    print("  ✅ Position sizer OK!")


def test_drawdown_tracker():
    """Test du drawdown tracker"""
    print("\n" + "="*60)
    print("📉 TEST: Drawdown Tracker")
    print("="*60)

    manager = PropFirmManager(
        prop_firm="APEX",
        account_size="50K",
        mode="EVALUATION"
    )

    # État initial
    state = manager.drawdown_tracker.get_state()
    print(f"\n  État initial:")
    print(f"    - Balance: ${state.current_balance:,.2f}")
    print(f"    - HWM: ${state.high_water_mark:,.2f}")
    print(f"    - DD Used: {state.dd_used_percent:.1f}%")
    print(f"    - Status: {state.status.value}")
    print(f"    - Can Trade: {state.can_trade}")

    # Simuler un profit
    manager.drawdown_tracker.update(51000)
    state = manager.drawdown_tracker.get_state()
    print(f"\n  Après +$1000:")
    print(f"    - Balance: ${state.current_balance:,.2f}")
    print(f"    - HWM: ${state.high_water_mark:,.2f}")
    print(f"    - DD Used: {state.dd_used_percent:.1f}%")

    # Simuler une perte
    manager.drawdown_tracker.update(49500)
    state = manager.drawdown_tracker.get_state()
    print(f"\n  Après -$1500:")
    print(f"    - Balance: ${state.current_balance:,.2f}")
    print(f"    - HWM: ${state.high_water_mark:,.2f}")
    print(f"    - DD Used: {state.dd_used_percent:.1f}%")
    print(f"    - Status: {state.status.value}")

    print("  ✅ Drawdown tracker OK!")


def test_can_trade():
    """Test de la vérification can_trade"""
    print("\n" + "="*60)
    print("🚦 TEST: Can Trade Check")
    print("="*60)

    manager = PropFirmManager(
        prop_firm="APEX",
        account_size="50K",
        mode="EVALUATION"
    )

    result = manager.can_trade()
    print(f"\n  Can Trade: {result['allowed']}")
    if result['warnings']:
        print(f"  Warnings: {result['warnings']}")
    if result['reasons']:
        print(f"  Reasons: {result['reasons']}")

    print("  ✅ Can trade check OK!")


def test_trade_recording():
    """Test de l'enregistrement des trades"""
    print("\n" + "="*60)
    print("💰 TEST: Trade Recording")
    print("="*60)

    manager = PropFirmManager(
        prop_firm="APEX",
        account_size="50K",
        mode="EVALUATION"
    )

    # Créer un trade gagnant
    trade1 = Trade(
        trade_id="T001",
        symbol="MES",
        direction=TradeDirection.LONG,
        contracts=2,
        entry_price=5950.25,
        entry_time=datetime.now(),
        session="POWER_HOUR",
        strategy="GEX_BOUNCE",
        confidence=0.85,
        initial_stop_ticks=12,
        initial_target_ticks=24,
    )
    trade1.close(exit_price=5956.25, exit_time=datetime.now(), commissions=2.50)

    print(f"\n  Trade 1: {trade1}")

    status = manager.record_trade(trade1)
    print(f"  Balance après: ${status['evaluation']['current_balance']:,.2f}")
    print(f"  PnL Total: ${status['evaluation']['total_pnl']:+,.2f}")
    print(f"  Progress: {status['evaluation']['progress']['percent']:.1f}%")

    # Créer un trade perdant
    trade2 = Trade(
        trade_id="T002",
        symbol="MES",
        direction=TradeDirection.SHORT,
        contracts=2,
        entry_price=5960.00,
        entry_time=datetime.now(),
        session="US_MORNING",
        strategy="GEX_FADE",
        confidence=0.70,
        initial_stop_ticks=10,
    )
    trade2.close(exit_price=5965.00, exit_time=datetime.now(), commissions=2.50)

    print(f"\n  Trade 2: {trade2}")

    status = manager.record_trade(trade2)
    print(f"  Balance après: ${status['evaluation']['current_balance']:,.2f}")
    print(f"  PnL Total: ${status['evaluation']['total_pnl']:+,.2f}")
    print(f"  Trades: {status['evaluation']['trades']['total']}")
    print(f"  Win Rate: {status['evaluation']['trades']['win_rate']:.1f}%")

    print("  ✅ Trade recording OK!")


def test_daily_report():
    """Test du rapport journalier"""
    print("\n" + "="*60)
    print("📊 TEST: Daily Report")
    print("="*60)

    manager = PropFirmManager(
        prop_firm="APEX",
        account_size="50K",
        mode="EVALUATION"
    )

    # Ajouter quelques trades
    for i in range(3):
        trade = Trade(
            trade_id=f"T{i+1:03d}",
            symbol="MES",
            direction=TradeDirection.LONG if i % 2 == 0 else TradeDirection.SHORT,
            contracts=2,
            entry_price=5950.00 + i * 5,
            entry_time=datetime.now(),
            session="POWER_HOUR",
            initial_stop_ticks=12,
        )
        # Gagner 2 sur 3
        exit_diff = 6 if i < 2 else -3
        trade.close(exit_price=trade.entry_price + exit_diff, exit_time=datetime.now())
        manager.record_trade(trade)

    report = manager.get_daily_report()
    print(report)

    print("  ✅ Daily report OK!")


def main():
    """Exécute tous les tests"""
    print("\n" + "="*60)
    print("🧪 MODULE PROP FIRM - TESTS")
    print("="*60)

    try:
        test_contract_specs()
        test_prop_firm_config()
        test_position_sizer()
        test_drawdown_tracker()
        test_can_trade()
        test_trade_recording()
        test_daily_report()

        print("\n" + "="*60)
        print("✅ TOUS LES TESTS PASSÉS!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
