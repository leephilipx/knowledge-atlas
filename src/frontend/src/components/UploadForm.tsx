import React, { useState } from 'react';
import { Form, Input, Upload, Button, message, Row, Col, Select, Typography, DatePicker, UploadFile } from 'antd';
import { UploadOutlined, LinkOutlined, DeleteOutlined } from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';

const { TextArea } = Input;
const { Text } = Typography;

const API_UPLOAD_URL = '/api/upload';

// --- 1. Type Definitions ---

// Define the common structure for staged items (both files and links)
interface StagedItem {
  uid: string; // Unique ID for keying/tracking in state
  name: string; // Filename or URL
  type: 'image' | 'link';
  theme: string;
  entryDate: string; // YYYY-MM format
}

// Define the structure specifically for staged files (includes the file object)
interface StagedFileItem extends StagedItem {
  type: 'image';
  file: File; // The actual file object
}

// Define the structure specifically for staged links
interface StagedLinkItem extends StagedItem {
  type: 'link';
  url: string; // The link URL
}

type StagingData = StagedFileItem | StagedLinkItem;

const UploadForm: React.FC = () => {
  const [form] = Form.useForm();
  const [stagedItems, setStagedItems] = useState<StagingData[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);

  // --- 2. Staging Handlers ---

  // Custom handler for file upload staging
  const handleFileChange = ({ fileList }: { fileList: UploadFile[] }) => {
    // Filter out files that are already staged based on AntD's unique UID
    const newFileItems: StagedFileItem[] = fileList
      .filter(file => file.status === 'uploading' && !stagedItems.some(item => item.uid === file.uid))
      .map(file => ({
        uid: file.uid,
        name: file.name,
        type: 'image',
        file: file.originFileObj as File, // OriginFileObj is a File object
        theme: 'General',
        entryDate: dayjs().format('YYYY-MM'),
      }));
    
    // We only update the state with new files; existing files' metadata remains untouched
    setStagedItems(prev => {
        // Filter out any files that were removed in the AntD component but not in our state
        const remainingUids = fileList.map(f => f.uid);
        const filteredPrev = prev.filter(item => item.type === 'link' || remainingUids.includes(item.uid));

        return [...filteredPrev, ...newFileItems];
    });
  };
  
  // Custom handler for link input staging
  const handleStageLinks = () => {
    const linksText = form.getFieldValue('links');
    if (!linksText) return;

    const newLinks: StagedLinkItem[] = linksText.split('\n')
      .map((l: string) => l.trim())
      .filter((l: string) => l.length > 0)
      .map((l: string) => ({
        uid: `link-${Date.now()}-${Math.random()}`,
        name: l,
        type: 'link',
        url: l,
        theme: 'General',
        entryDate: dayjs().format('YYYY-MM'),
      }));

    setStagedItems(prev => [...prev, ...newLinks]);
    form.setFieldsValue({ links: '' }); // Clear the text area
  };

  // --- 3. Metadata Editing & Removal ---

  const handleMetadataChange = (uid: string, field: keyof StagingData, value: string | null) => {
    setStagedItems(prev => prev.map(item => 
      item.uid === uid ? { ...item, [field]: value } : item
    ));
  };
  
  const handleRemove = (uid: string) => {
     setStagedItems(prev => prev.filter(item => item.uid !== uid));
  };

  // --- 4. Final Submission Logic ---

  const handleSubmit = async () => {
    if (stagedItems.length === 0) {
      message.warning('Please stage files or links first.');
      return;
    }

    setUploading(true);
    let successCount = 0;

    for (const item of stagedItems) {
      const formData = new FormData();
      formData.append('type', item.type);
      formData.append('theme', item.theme);
      formData.append('entryDate', item.entryDate);
      
      if (item.type === 'image') {
        // StagedFileItem has the file property
        formData.append('file', (item as StagedFileItem).file);
      } else if (item.type === 'link') {
        // StagedLinkItem has the url property
        formData.append('url', (item as StagedLinkItem).url);
      }

      try {
        await axios.post(API_UPLOAD_URL, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        successCount++;
      } catch (error) {
        console.error(`Failed to process item ${item.name}:`, error);
      }
    }

    setUploading(false);
    if (successCount > 0) {
      message.success(`Successfully added and queued ${successCount} items for processing!`);
      setStagedItems([]);
    } else {
      message.error('All uploads failed or no items were processed.');
    }
  };

  // --- 5. Render Functions for Staged Items ---

  const renderStagedItems = (items: StagingData[]) => (
    <div style={{ maxHeight: 400, overflowY: 'auto', border: '1px solid #e8e8e8', padding: 16 }}>
      {items.map(item => (
        <Row key={item.uid} gutter={16} style={{ marginBottom: 12, borderBottom: '1px dotted #f0f0f0', paddingBottom: 8, alignItems: 'center' }}>
          <Col span={8}>
            <Text strong>{item.name}</Text>
            <br />
            <Text type="secondary">{item.type.toUpperCase()}</Text>
          </Col>
          <Col span={5}>
            <Select
              value={item.theme}
              style={{ width: '100%' }}
              options={['General', 'Science', 'Tech', 'Finance', 'Other'].map(t => ({ value: t, label: t }))}
              onChange={(value) => handleMetadataChange(item.uid, 'theme', value)}
            />
          </Col>
          <Col span={5}>
            <DatePicker 
                picker="month" 
                format="YYYY-MM"
                // Parse the string date back into a Dayjs object for the DatePicker component
                defaultValue={dayjs(item.entryDate, 'YYYY-MM')}
                onChange={(date, dateString) => handleMetadataChange(item.uid, 'entryDate', dateString)}
                style={{ width: '100%' }}
            />
          </Col>
          <Col span={4}>
            <Button 
                type="text" 
                icon={<DeleteOutlined />} 
                onClick={() => handleRemove(item.uid)}
                danger
            />
          </Col>
        </Row>
      ))}
    </div>
  );

  return (
    <>
      <h2>Add New Knowledge Entries</h2>
      <Form form={form} layout="vertical">
        <Row gutter={24}>
          <Col span={12}>
            <Form.Item label="Upload Files (Images)">
              <Upload.Dragger
                multiple={true}
                accept=".jpg,.jpeg,.png"
                beforeUpload={() => false} // Prevent automatic upload
                onChange={handleFileChange}
                showUploadList={false} 
              >
                <p className="ant-upload-drag-icon"><UploadOutlined /></p>
                <p className="ant-upload-text">Click or drag image files to this area</p>
              </Upload.Dragger>
            </Form.Item>
          </Col>

          <Col span={12}>
            <Form.Item label="Paste Links (One per line)" name="links">
              <TextArea rows={5} placeholder="e.g., https://example.com/article1" />
            </Form.Item>
            <Button type="primary" icon={<LinkOutlined />} onClick={handleStageLinks} style={{ marginBottom: 20 }}>
              Stage Links for Review
            </Button>
          </Col>
        </Row>
      </Form>

      {/* Staged Items Review */}
      {(stagedItems.length > 0) && (
        <>
          <h3>Review Staged Items ({stagedItems.length})</h3>
          <Row gutter={16} style={{ marginBottom: 10, fontWeight: 'bold' }}>
            <Col span={8}>Item</Col>
            <Col span={5}>Theme</Col>
            <Col span={5}>Est. Date</Col>
            <Col span={4}>Action</Col>
          </Row>
          {renderStagedItems(stagedItems)} 
          
          <Button
            type="primary"
            size="large"
            style={{ marginTop: 20 }}
            onClick={handleSubmit}
            loading={uploading}
          >
            Confirm & Start Processing All
          </Button>
        </>
      )}
    </>
  );
};

export default UploadForm;