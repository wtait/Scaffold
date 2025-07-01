"use client";
import {
  Avatar,
  BreadcrumbItem,
  Breadcrumbs,
  Icon,
  Menu,
  MenuContent,
  MenuGroup,
  MenuItem,
  MenuTrigger,
  Typography,
} from "@beamcloud/design-system";
import styled from "styled-components";
import { faServer } from "@fortawesome/pro-regular-svg-icons";

const Header = () => {
  return (
    <Container>
      <BreadcrumbsWrapper>
        <Breadcrumbs
          separatorImageDimension="20px"
          separatorImageSrc="/static/slash.svg"
        >
          <BreadcrumbItem>
            <Icon icon={faServer} size="sm" color="gray14" />
          </BreadcrumbItem>
        </Breadcrumbs>
      </BreadcrumbsWrapper>
      <Navigation>
        <Menu>
          <StyledMenuTrigger>
            <Avatar name={"Test"} />
          </StyledMenuTrigger>
          <MenuContent align="end" sideOffset={4} minWidth="360px">
            <MenuGroup>
              <MenuItem>
                <Typography tag="span" variant="textXs" color="gray11">
                  Organization
                </Typography>
                <Typography tag="span" variant="textSmPlus" color="gray12">
                  Test
                </Typography>
              </MenuItem>
            </MenuGroup>
          </MenuContent>
        </Menu>
      </Navigation>
    </Container>
  );
};

export default Header;

const Container = styled.header`
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px 4px 20px;
  gap: 24px;
  width: 100%;
  flex-shrink: 0;
  background-color: ${({ theme }) => theme.colors.gray5};
`;

const BreadcrumbsWrapper = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 0px;
  gap: 10px;
`;

const Navigation = styled.div`
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  align-items: center;
  padding: 0px;
  gap: 20px;
  margin-bottom: 10px;
`;

const ChevronIcon = styled(Icon)`
  && {
    color: inherit;
    transition: transform 0.2s linear;
  }
`;

const StyledMenuTrigger = styled(MenuTrigger)`
  && {
    width: max-content;
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: center;
    padding: 0px;
    gap: 8px;
    cursor: pointer;
    color: ${(props) => props.theme.colors.gray11};
    &:hover {
      color: ${(props) => props.theme.colors.gray12};
    }

    &[data-state="open"] ${ChevronIcon} {
      transform: rotate(180deg);
    }
  }
`;
