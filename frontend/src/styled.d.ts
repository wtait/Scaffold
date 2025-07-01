import 'styled-components';
import { Theme as DesignSystemTheme } from '@beamcloud/design-system';

declare module 'styled-components' {
  export interface DefaultTheme extends DesignSystemTheme {}
} 