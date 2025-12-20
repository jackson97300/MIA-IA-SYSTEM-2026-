"""
Position Sizer intelligent pour Prop Firm
RÈGLE D'OR: Risquer 0.5-1% du DRAWDOWN DISPONIBLE par trade (pas du compte!)
"""
from dataclasses import dataclass
from typing import Optional, List

from ..config.prop_firm_rules import get_prop_firm_config, get_account_config
from ..config.contract_specs import get_contract_spec, CONTRACT_SPECS
from ..config.risk_parameters import RiskParameters, get_risk_params


@dataclass
class PositionSize:
    """Résultat du calcul de position size"""
    symbol: str
    contracts: int
    is_micro: bool
    risk_per_contract: float
    total_risk: float
    risk_percent_of_dd: float
    max_allowed: int
    stop_loss_ticks: int
    stop_loss_dollars: float
    recommendation: str
    warnings: List[str]


class PropFirmPositionSizer:
    """
    Calcule la taille de position optimale pour les prop firms

    RÈGLE D'OR DES PROS:
    - Risquer 0.5-1% du DRAWDOWN DISPONIBLE (pas du compte total!)
    - Utiliser les MICROS en évaluation
    - "Traders who risk <2% are 40% more likely to pass"
    """

    def __init__(
        self,
        prop_firm: str,
        account_size: str,
        mode: str = "EVALUATION",
        risk_params: Optional[RiskParameters] = None
    ):
        self.prop_firm = prop_firm
        self.account_size = account_size
        self.mode = mode

        # Charger les configurations
        self.firm_config = get_prop_firm_config(prop_firm)
        self.account_config = get_account_config(prop_firm, account_size)
        self.risk_params = risk_params or get_risk_params(mode)

        # État du compte (sera mis à jour par le DrawdownTracker)
        self.starting_balance = self.account_config["starting_balance"]
        self.current_balance = self.starting_balance
        self.high_water_mark = self.starting_balance
        self.trailing_dd = self.account_config["trailing_dd"]

    def update_account_state(self, current_balance: float, high_water_mark: float):
        """Met à jour l'état du compte (appelé par DrawdownTracker)"""
        self.current_balance = current_balance
        self.high_water_mark = high_water_mark

    def calculate_available_drawdown(self) -> float:
        """
        Calcule le drawdown DISPONIBLE (pas le total!)
        C'est sur cette base qu'on calcule le risque par trade
        """
        # Floor = high water mark - trailing DD
        floor = self.high_water_mark - self.trailing_dd
        # Drawdown disponible = balance actuelle - floor
        available = self.current_balance - floor
        return max(0, available)

    def calculate_max_risk_per_trade(self) -> float:
        """
        Calcule le risque maximum par trade en $
        Basé sur % du drawdown DISPONIBLE
        """
        available_dd = self.calculate_available_drawdown()
        risk_percent = self.risk_params.risk_per_trade_percent

        max_risk = available_dd * (risk_percent / 100)

        # Override si défini
        if self.risk_params.max_risk_per_trade_dollars:
            max_risk = min(max_risk, self.risk_params.max_risk_per_trade_dollars)

        return max_risk

    def calculate_position_size(
        self,
        symbol: str,
        stop_loss_ticks: int,
        prefer_micros: Optional[bool] = None
    ) -> PositionSize:
        """
        Calcule le nombre de contrats optimal

        Args:
            symbol: Symbole du contrat (ES, NQ, MES, MNQ, etc.)
            stop_loss_ticks: Distance du stop loss en ticks
            prefer_micros: Force l'utilisation des micros (défaut: selon risk_params)

        Returns:
            PositionSize avec tous les détails
        """
        use_micros = prefer_micros if prefer_micros is not None else self.risk_params.use_micros

        # Déterminer le symbole à utiliser
        spec = get_contract_spec(symbol)
        if use_micros and not spec.is_micro and spec.micro_equivalent:
            # Convertir en micro
            symbol = spec.micro_equivalent
            spec = get_contract_spec(symbol)

        # Calculer le risque maximum
        max_risk = self.calculate_max_risk_per_trade()

        # Risque par contrat = stop_loss_ticks * tick_value
        risk_per_contract = stop_loss_ticks * spec.tick_value

        # Nombre de contrats (arrondi vers le BAS pour sécurité!)
        if risk_per_contract > 0:
            contracts = int(max_risk / risk_per_contract)
        else:
            contracts = 0

        # Vérifier les limites de la prop firm
        if spec.is_micro:
            max_allowed = self.account_config.get("max_micros", self.account_config["max_contracts"] * 10)
        else:
            max_allowed = self.account_config["max_contracts"]

        # Override si défini dans risk_params
        if self.risk_params.max_contracts_per_trade:
            max_allowed = min(max_allowed, self.risk_params.max_contracts_per_trade)

        contracts = min(contracts, max_allowed)

        # Calculs finaux
        total_risk = contracts * risk_per_contract
        risk_percent_of_dd = (total_risk / self.trailing_dd * 100) if self.trailing_dd > 0 else 0
        stop_loss_dollars = stop_loss_ticks * spec.tick_value

        # Warnings
        warnings = []
        if contracts == 0:
            warnings.append("⚠️ Risque insuffisant pour même 1 contrat avec ce stop loss")
        if risk_percent_of_dd > 2:
            warnings.append(f"⚠️ Risque élevé: {risk_percent_of_dd:.1f}% du DD")
        if not spec.is_micro and use_micros:
            warnings.append("💡 Considérer utiliser les micros pour meilleur contrôle")

        # Recommandation
        recommendation = self._generate_recommendation(symbol, contracts, spec, stop_loss_ticks)

        return PositionSize(
            symbol=symbol,
            contracts=contracts,
            is_micro=spec.is_micro,
            risk_per_contract=risk_per_contract,
            total_risk=total_risk,
            risk_percent_of_dd=risk_percent_of_dd,
            max_allowed=max_allowed,
            stop_loss_ticks=stop_loss_ticks,
            stop_loss_dollars=stop_loss_dollars,
            recommendation=recommendation,
            warnings=warnings,
        )

    def _generate_recommendation(
        self,
        symbol: str,
        contracts: int,
        spec,
        stop_loss_ticks: int
    ) -> str:
        """Génère une recommandation textuelle"""
        if contracts == 0:
            # Suggérer les micros si on trade des minis
            if not spec.is_micro and spec.micro_equivalent:
                micro_spec = get_contract_spec(spec.micro_equivalent)
                micro_risk = stop_loss_ticks * micro_spec.tick_value
                max_risk = self.calculate_max_risk_per_trade()
                possible_micros = int(max_risk / micro_risk) if micro_risk > 0 else 0
                return f"💡 Impossible avec {symbol}. Utiliser {possible_micros} {spec.micro_equivalent} à la place."
            return "❌ Stop loss trop large pour le risque disponible"

        if not spec.is_micro and spec.micro_equivalent:
            micro_qty = contracts * 10
            return f"💡 CONSEIL PRO: {micro_qty} {spec.micro_equivalent} au lieu de {contracts} {symbol} pour meilleur contrôle"

        return f"✅ {contracts} {symbol} = risque optimal"

    def get_sizing_table(self, symbol: str, stop_losses: list = None) -> dict:
        """
        Génère un tableau de sizing pour différents stop losses
        Utile pour la planification
        """
        if stop_losses is None:
            stop_losses = [8, 10, 12, 15, 20, 25, 30]

        table = {
            "symbol": symbol,
            "max_risk": self.calculate_max_risk_per_trade(),
            "available_dd": self.calculate_available_drawdown(),
            "sizes": {}
        }

        for sl in stop_losses:
            size = self.calculate_position_size(symbol, sl)
            table["sizes"][sl] = {
                "contracts": size.contracts,
                "total_risk": size.total_risk,
                "risk_percent": size.risk_percent_of_dd,
            }

        return table

