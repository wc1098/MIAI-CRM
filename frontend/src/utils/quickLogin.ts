import { AUTH_KEYS } from "@/constants";
import { Storage } from "@/utils/storage";
import type { AutoLoginUser, QuickLoginDeviceResult } from "@/api/module_system/auth";

export interface QuickLoginAccount extends AutoLoginUser {
  user_id: number;
  device_token: string;
  expires_at: string;
  last_login_at: string;
}

function isValidAccount(account: QuickLoginAccount): boolean {
  return Boolean(
    account &&
    account.user_id &&
    account.username &&
    account.name &&
    account.device_token &&
    account.expires_at &&
    new Date(account.expires_at).getTime() > Date.now()
  );
}

export class QuickLoginStorage {
  static getAccounts(): QuickLoginAccount[] {
    const accounts = Storage.get<QuickLoginAccount[]>(AUTH_KEYS.QUICK_LOGIN_ACCOUNTS, []);
    const validAccounts = Array.isArray(accounts) ? accounts.filter(isValidAccount) : [];
    if (validAccounts.length !== accounts.length) {
      Storage.set(AUTH_KEYS.QUICK_LOGIN_ACCOUNTS, validAccounts);
    }
    return validAccounts;
  }

  static saveDevice(result: QuickLoginDeviceResult): QuickLoginAccount {
    const account: QuickLoginAccount = {
      ...result.user,
      user_id: result.user.id,
      device_token: result.device_token,
      expires_at: result.expires_at,
      last_login_at: new Date().toISOString(),
    };

    const accounts = this.getAccounts().filter((item) => item.user_id !== account.user_id);
    accounts.unshift(account);
    Storage.set(AUTH_KEYS.QUICK_LOGIN_ACCOUNTS, accounts);
    return account;
  }

  static removeAccount(userId: number): void {
    Storage.set(
      AUTH_KEYS.QUICK_LOGIN_ACCOUNTS,
      this.getAccounts().filter((account) => account.user_id !== userId)
    );
  }
}
