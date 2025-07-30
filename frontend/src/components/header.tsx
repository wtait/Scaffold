"use client";

import { Breadcrumb, BreadcrumbItem, BreadcrumbList } from "./ui/breadcrumb";
import {
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@radix-ui/react-dropdown-menu";
import { MenuIcon, ServerIcon } from "lucide-react";

import { DropdownMenu } from "./ui/dropdown-menu";
import { DropdownMenuGroup } from "@radix-ui/react-dropdown-menu";
import { DropdownMenuItem } from "@radix-ui/react-dropdown-menu";
import styled from "styled-components";

const Header = () => {
  return (
    <Container>
      <BreadcrumbsWrapper>
        <BreadcrumbList>
          <Breadcrumb>
            <BreadcrumbItem>
              <ServerIcon />
            </BreadcrumbItem>
          </Breadcrumb>
        </BreadcrumbList>
      </BreadcrumbsWrapper>
      <Navigation>
        <DropdownMenu>
          <DropdownMenuTrigger>
            <MenuIcon />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" sideOffset={4}>
            <DropdownMenuGroup>
              <DropdownMenuItem>
                <span>Organization</span>
                <span>Test</span>
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
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
