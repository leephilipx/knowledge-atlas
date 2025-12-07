import React from 'react';
import { Layout, Menu } from 'antd';
import DashboardTable from './components/DashboardTable';
import UploadForm from './components/UploadForm';

const { Content, Header } = Layout;

const items = [
  { key: '1', label: '📊 Dashboard' },
  { key: '2', label: '📤 Upload' },
];

function App() {
  const [current, setCurrent] = React.useState('1');

  const renderContent = () => {
    switch (current) {
      case '1':
        return <DashboardTable />;
      case '2':
        return <UploadForm />;
      default:
        return null;
    }
  };

  return (
    <Layout>
      <Header style={{ display: 'flex', alignItems: 'center', backgroundColor: '#fff' }}>
        <div style={{ fontSize: '1.5em', fontWeight: 'bold' }}>Knowledge Atlas</div>
        <Menu
          onClick={(e) => setCurrent(e.key)}
          selectedKeys={[current]}
          mode="horizontal"
          items={items}
          style={{ flex: 1, minWidth: 0, marginLeft: 20 }}
        />
      </Header>
      <Content style={{ padding: '0 50px', minHeight: 'calc(100vh - 64px)' }}>
        <div style={{ background: '#fff', padding: 24, minHeight: 600, marginTop: 24 }}>
          {renderContent()}
        </div>
      </Content>
    </Layout>
  );
}

export default App;