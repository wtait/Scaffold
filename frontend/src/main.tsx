import "./index.css";

import {
  ThemeProvider as ThemeContainer,
  defaultTheme,
} from "@beamcloud/design-system";

import App from "./App";
import { BrowserRouter } from "react-router-dom";
import { StrictMode } from "react";
import { ThemeProvider } from "styled-components";
import { createRoot } from "react-dom/client";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider theme={defaultTheme}>
        <ThemeContainer>
          <App />
        </ThemeContainer>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>
);
