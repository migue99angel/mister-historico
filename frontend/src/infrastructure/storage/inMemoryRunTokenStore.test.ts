import { describeRunTokenStoreContract } from './run-token-store.contract';
import { createInMemoryRunTokenStore } from './inMemoryRunTokenStore';

describeRunTokenStoreContract('createInMemoryRunTokenStore', createInMemoryRunTokenStore);
