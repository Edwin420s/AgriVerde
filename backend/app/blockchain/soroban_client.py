from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.soroban import SorobanServer, SorobanTransactionBuilder, Contract, Address
from app.core.config import settings
from app.core.logging import logger

class SorobanClient:
    def __init__(self):
        self.server = Server(horizon_url=settings.STELLAR_HORIZON_URL)
        self.soroban_server = SorobanServer(settings.STELLAN_RPC_URL)  # RPC URL for Soroban
        self.contract_id = settings.SOROBAN_CONTRACT_ID
        self.source_keypair = Keypair.from_secret(settings.STELLAR_SECRET_KEY)
        self.network_passphrase = Network.TESTNET if settings.STELLAR_NETWORK == "testnet" else Network.PUBLIC

    def commit_dataset(self, dataset_id: str, data_hash: str) -> str:
        """
        Invokes the Soroban contract to store a dataset commitment.
        Returns the transaction hash.
        """
        contract = Contract(contract_id=self.contract_id)
        # Build the transaction with the contract call
        tx_builder = SorobanTransactionBuilder(
            source_secret=settings.STELLAR_SECRET_KEY,
            network_passphrase=self.network_passphrase,
            base_fee=100,
            soroban_server=self.soroban_server
        )
        # The contract function signature: commit(dataset_id: String, data_hash: String) -> void
        tx = tx_builder.build_soroban_transaction(
            contract=contract,
            function_name="commit",
            args=[dataset_id, data_hash],
            source_account=self.source_keypair.public_key
        )
        # Sign and submit
        signed_tx = tx.sign(self.source_keypair)
        response = tx_builder.submit(signed_tx)
        logger.info(f"Soroban commitment submitted: {response['id']}")
        return response["id"]  # transaction hash

# Singleton instance
soroban_client = SorobanClient()

def submit_commitment(dataset_id: str, data_hash: str) -> str:
    return soroban_client.commit_dataset(dataset_id, data_hash)