// config.js
export const runtimeEnvConfig = {
    guiData: process.env.GUI_DATA,
    userDatabase: process.env.USERDATABASE,
    actions: process.env.Actions,
    endpoints: {
        s1Get: process.env.S1_GET,
        s2Get: process.env.S2_GET,
        s1Update: process.env.S1_UPDATE,
        s2Update: process.env.S2_UPDATE,
    }
}