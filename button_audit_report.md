# Button Audit Report

- total buttons: 81
- with click handler: 81
- without handler: 0
- destructive buttons: 11
- confirmation dialogs: 10

## Destructive Buttons

- 清空报告 (clearButton) @ line 3350
- 清空勾选 (clearSelectionButton) @ line 4497
- 批量删除 (batchDeleteButton) @ line 4340
- 停止连续测试 (stopContinuousButton) @ line 4428
- 清空报告 (reportClearButton) @ line 4579
- 删除 (del) @ line 4099
- 清空全部 (clearAllButton) @ line 5453
- 删除已选 (deleteSelectedButton) @ line 6026
- 清空勾选 (clearSelectedButton) @ line 6054
- 清空本次选择 (resetButton) @ line 7549
- 清空自定义 (clearCustomButton) @ line 7571

## Confirmation Dialogs

- del @ line 4100: const confirmed = window.confirm(`将删除预设「${preset.name}」，确定继续吗？`);
- batchDeleteButton @ line 4346: const confirmed = window.confirm(`将删除已勾选的 ${targetIds.length} 个预设，此操作不可撤销。确定继续吗？`);
- reportClearButton @ line 4581: const confirmed = window.confirm(`将清空当前 ${continuousRunReport.length} 条连续测试事件，确定继续吗？`);
- del @ line 5342: const confirmed = window.confirm("将删除这条历史记录，确定继续吗？");
- clearAllButton @ line 5453: clearAllButton.onclick=()=>{ const historyCount=getNodeHistory(node).length; if(historyCount>0){ const confirmed=window.confirm(`将清空全部 ${historyCount} 条随机历史，确定继续吗？`); if(!confirmed){ statusEl.textContent="已取消清空全部历史。"; return; } } setNodeHistory(node, []); statusEl.textContent="已清空全部随机历史。"; render(); };
- clearButton @ line 5454: clearButton.onclick=()=>{ const historyCount=getNodeHistory(node).length; if(historyCount>0){ const confirmed=window.confirm(`将清空当前历史记录（${historyCount} 条），确定继续吗？`); if(!confirmed){ statusEl.textContent="已取消清空历史。"; return; } } setNodeHistory(node, []); statusEl.textContent="已清空历史。"; render(); };
- deleteSelectedButton @ line 6032: const confirmed = window.confirm(`将删除已勾选的 ${keys.length} 个标签，确定继续吗？`);
- clearSelectedButton @ line 6056: const confirmed = window.confirm(`将清空当前 ${selectedTagKeys.size} 个勾选项，确定继续吗？`);
- resetButton @ line 7553: const confirmed = window.confirm("将清空本次已选标签和自定义补充，确定继续吗？");
- clearCustomButton @ line 7573: const confirmed = window.confirm("将清空当前自定义补充标签，确定继续吗？");