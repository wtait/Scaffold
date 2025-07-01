import "./App.css";
import styled from "styled-components";
import { Routes, Route } from "react-router-dom";
import CreateRoute from "./screens/Create";
import NewScreen from "./screens/New";

const App: React.FC = () => {
  return (
    <Container>
      {/* <Header /> */}
      <ContentContainer>
        <Routes>
          <Route path="/" element={<NewScreen />} />
          <Route path="/create" element={<CreateRoute />} />
        </Routes>
      </ContentContainer>
    </Container>
  );
};

export default App;

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: start;
  width: 100vw;
  height: 100vh;
  background-color: ${({ theme }) => theme.colors.gray3};
  overflow: hidden;
`;

const ContentContainer = styled.div`
  width: 100%;
  flex-grow: 1;
  overflow: auto;
`;
