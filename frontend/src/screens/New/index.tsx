import React, { useState } from "react";

import { Textarea } from "@/components/ui/textarea";
import styled from "styled-components";
import { useNavigate } from "react-router-dom";

const NewScreen: React.FC = () => {
  const [input, setInput] = useState("");
  const navigate = useNavigate();

  const handleStartBuilding = () => {
    if (input.trim()) {
      navigate("/create", { state: { initialPrompt: input } });
    }
  };

  return (
    <Outer>
      <CenterColumn>
        <LogoTitleGroup>
          <h1 className="text-2xl font-bold">What do you want build?</h1>
          <p className="text-lg font-normal">
            Build a website with Beam Sandboxes.
          </p>
        </LogoTitleGroup>
        <PromptCard>
          <TextareaWrapper>
            <PaperclipIcon />
            <Textarea
              rows={3}
              placeholder="What do you want to build?"
              value={input}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                setInput(e.target.value)
              }
              onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleStartBuilding();
                }
              }}
            />
            <RunButton>
              <button onClick={handleStartBuilding}>Start Building</button>
            </RunButton>
          </TextareaWrapper>
        </PromptCard>
        <TemplatesSection>
          <TemplatesHeader>
            <h2 style={{ marginBottom: 8 }}>Quickstart templates</h2>
            <p>
              Get started instantly with a framework or integration of your
              choice.
            </p>
          </TemplatesHeader>
        </TemplatesSection>
      </CenterColumn>
    </Outer>
  );
};

export default NewScreen;

const Outer = styled.div`
  min-height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const CenterColumn = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100vw;
  max-width: 100vw;
  margin-top: 64px;
`;

const LogoTitleGroup = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 0px;
`;

const PromptCard = styled.div`
  border-radius: 22px;
  padding: 0px 0px 0px 0px;
  height: 150px;
  width: 100%;
  max-width: 600px;
  margin-bottom: 28px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
`;

const TextareaWrapper = styled.div`
  position: relative;
  width: 100%;
  min-height: 90px;
  display: flex;
  align-items: stretch;
`;

// const StyledTextarea = styled(Input)`
//   background: ${({ theme }) => theme.colors.gray2};
//   border: 1.5px solid ${({ theme }) => theme.colors.gray6};
//   border-radius: 16px;
//   color: ${({ theme }) => theme.colors.gray12};
//   font-family: ${({ theme }) =>
//     theme?.typography?.fontFamily?.primary || "Inter, system-ui, sans-serif"};
//   font-weight: 400;
//   width: 100%;
//   min-height: 150px;
//   padding: 20px 2px 2px 12px;
//   resize: none;
//   box-shadow: none;

//   &::placeholder {
//     color: ${({ theme }) => theme.colors.gray11};
//     opacity: 1;
//     font-weight: 400;
//   }
// `;

const PaperclipIcon = styled.div`
  position: absolute;
  left: 14px;
  bottom: 16px;
  z-index: 2;
  font-size: 20px;
`;

const RunButton = styled.div`
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 2;
`;

const TemplatesSection = styled.div`
  width: 100%;
  max-width: 1200px;
  margin-top: 0px;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const TemplatesHeader = styled.div`
  margin-left: 0;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
`;
