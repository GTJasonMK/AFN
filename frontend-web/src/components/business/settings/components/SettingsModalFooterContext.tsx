import React from 'react';

type SettingsModalFooterApi = {
  setFooter: (footer: React.ReactNode | null) => void;
};

const noopSetFooter: SettingsModalFooterApi['setFooter'] = () => undefined;

const SettingsModalFooterContext = React.createContext<SettingsModalFooterApi>({
  setFooter: noopSetFooter,
});

export const SettingsModalFooterProvider: React.FC<{
  setFooter: SettingsModalFooterApi['setFooter'];
  children: React.ReactNode;
}> = ({ setFooter, children }) => {
  return (
    <SettingsModalFooterContext.Provider value={{ setFooter }}>
      {children}
    </SettingsModalFooterContext.Provider>
  );
};

export const useSettingsModalFooter = () => React.useContext(SettingsModalFooterContext);

