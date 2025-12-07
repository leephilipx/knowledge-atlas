import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Space, message, Select, Input, TableProps } from 'antd';
import { ColumnsType } from 'antd/es/table';
import axios from 'axios';
import { Entry, ApiResponse, TablePagination } from '../types';

const API_BASE_URL = '/api/entries'; // Replace with your actual backend URL

const { Search } = Input;

// --- 2. Custom Status Renderer ---

const getStatusTag = (stage: Entry['process_stage']): React.ReactNode => {
  let color: string;
  switch (stage) {
    case 'Complete': color = 'green'; break;
    case 'Summarizing': color = 'blue'; break;
    case 'Preprocessing': color = 'geekblue'; break;
    case 'Error': color = 'red'; break;
    default: color = 'default';
  }
  return <Tag color={color}>{stage}</Tag>;
};

const DashboardTable: React.FC = () => {
  const [data, setData] = useState<Entry[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [pagination, setPagination] = useState<TablePagination>({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [searchText, setSearchText] = useState<string>('');

  // --- 3. Data Fetching Logic ---
  const fetchData = useCallback(async (current: number, pageSize: number, keyword: string) => {
    setLoading(true);
    try {
      const response = await axios.get<ApiResponse>(API_BASE_URL, {
        params: {
          page: current,
          limit: pageSize,
          keyword: keyword,
        },
      });

      setData(response.data.data);
      setPagination(prev => ({
        ...prev,
        total: response.data.total,
        current: current,
        pageSize: pageSize,
      }));
    } catch (error) {
      message.error('Failed to fetch data.');
      console.error(error);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(pagination.current, pagination.pageSize, searchText);
  }, [fetchData, pagination.pageSize, searchText]);

  // Handler for table changes (pagination, sorting)
  const handleTableChange: TableProps<Entry>['onChange'] = (newPagination) => {
    const { current, pageSize } = newPagination;
    
    // AntD's onChange can return undefined for current/pageSize on certain actions,
    // so we provide fallbacks to ensure type safety.
    const newCurrent = current ?? pagination.current;
    const newPageSize = pageSize ?? pagination.pageSize;

    setPagination(prev => ({...prev, current: newCurrent, pageSize: newPageSize}));
    // Explicitly call fetchData here to trigger the API call immediately
    fetchData(newCurrent, newPageSize, searchText);
  };

  // --- 4. Action Handlers ---
  const handleReprocess = async (id: string) => {
    try {
      await axios.post(`/api/reprocess/${id}`);
      message.success('Reprocessing job started.');
      fetchData(pagination.current, pagination.pageSize, searchText); // Refresh data
    } catch (error) {
      message.error('Reprocessing failed.');
    }
  };

  const handleEdit = (id: string, field: keyof Entry, value: string) => {
    // Implement API call to update metadata (theme or entry_date)
    message.info(`Editing ${field} for ${id} to ${value}. (Implement API call)`);
  };

  // --- 5. Table Columns Definition ---
  const columns: ColumnsType<Entry> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { 
      title: 'Theme', 
      dataIndex: 'theme', 
      key: 'theme', 
      render: (text: string, record: Entry) => (
        <Select
          defaultValue={text}
          style={{ width: 120 }}
          options={['General', 'Science', 'Tech', 'Finance', 'Other'].map(t => ({ value: t, label: t }))}
          onChange={(value) => handleEdit(record.id, 'theme', value)}
        />
    )},
    { title: 'Caption/Summary', dataIndex: 'summary_caption', key: 'summary_caption', ellipsis: true },
    { 
      title: 'Stage', 
      dataIndex: 'process_stage', 
      key: 'process_stage', 
      render: (stage: Entry['process_stage']) => getStatusTag(stage) 
    },
    { title: 'Entry Date', dataIndex: 'entry_date', key: 'entry_date', width: 120 },
    {
      title: 'Actions',
      key: 'action',
      width: 150,
      render: (_, record: Entry) => (
        <Space size="small">
          {record.process_stage !== 'Complete' && (
            <Button size="small" onClick={() => handleReprocess(record.id)} danger>
              Reprocess
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <h2>Repository Entries</h2>
      <Search
        placeholder="Search summary by keyword"
        allowClear
        onSearch={(value) => {
          setSearchText(value);
          // When searching, reset to page 1 to start fresh results
          setPagination(prev => ({...prev, current: 1}));
          fetchData(1, pagination.pageSize, value);
        }}
        style={{ width: 300, marginBottom: 20 }}
      />
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{...pagination, showSizeChanger: true}}
        onChange={handleTableChange}
        scroll={{ x: 'max-content' }}
      />
    </>
  );
};

export default DashboardTable;