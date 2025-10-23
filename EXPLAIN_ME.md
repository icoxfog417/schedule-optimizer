# 病院スケジューリング自動化システムの仕組み

## はじめに

このシステムは、病院で患者さんと理学療法士のスケジュールを自動的に組むためのプログラムです。
初級レベルの開発者向けに、技術的な背景から実装方法まで分かりやすく説明します。

## 1. 問題の概要

### 何を解決するのか？
- 患者さんが必要な理学療法の時間を確保する
- 理学療法士の勤務時間内で効率的にスケジュールを組む
- 患者さんの入浴や排泄などの制約を考慮する
- 担当療法士が不在の場合の代替療法士を適切に選ぶ

### なぜ難しいのか？
- 患者数×療法士数×時間枠の組み合わせが膨大
- 複数の制約条件を同時に満たす必要がある
- 手作業では時間がかかり、ミスが発生しやすい

## 2. 技術的なアプローチ

### 2.1 制約充足問題（Constraint Satisfaction Problem）として捉える

このスケジューリング問題は「制約充足問題」という数学的な問題として解くことができます。

**制約充足問題とは？**
- 変数（患者、療法士、時間枠）
- 各変数が取れる値の範囲（ドメイン）
- 満たすべき制約条件
- これらすべてを満たす解を見つける問題

### 2.2 行列（Matrix）を使った表現

複雑な制約条件を数値の行列で表現することで、コンピュータが効率的に計算できるようになります。

## 3. データ構造の設計

### 3.1 制約行列の種類

#### 患者可用性行列（Patient Availability Matrix）
```
患者 × 時間枠 の行列（例：50人 × 18枠）

        9:00  9:20  9:40  ...  16:40
患者A    1     1     0    ...    1     # 1=利用可能、0=利用不可
患者B    0     1     1    ...    0
患者C    1     1     1    ...    1
...
```

**なぜこの形？**
- 入浴時間、排泄時間、その他制約を一つの行列で表現
- 1と0で表現することで高速な計算が可能

#### 療法士可用性行列（Therapist Availability Matrix）
```
療法士 × 時間枠 の行列

          9:00  9:20  9:40  ...  16:40
療法士1    1     1     1    ...    1     # 〇（終日勤務）
療法士2    0     0     0    ...    1     # AN（午後のみ）
療法士3    1     1     1    ...    0     # PN（午前のみ）
...
```

#### 相性行列（Compatibility Matrix）
```
患者 × 療法士 の行列

        療法士1  療法士2  療法士3  ...
患者A    100      80      60    ...    # 100=担当療法士
患者B     20      100     40    ...    # スコアが高いほど適合
患者C     60       40     100   ...
...
```

**スコアの意味：**
- 100: 担当療法士
- 80: 同病棟・同性別
- 60: 同性別のみ
- 40: 同病棟のみ
- 20: 異病棟・異性別
- 0: 割り当て不可（専従制約違反）

### 3.2 要求時間ベクトル（Requirements Vector）
```python
requirements = [180, 120, 180, 120, ...]  # 各患者の必要時間（分）
# 脳血管疾患患者: 180分/日
# その他患者: 120分/日
```

## 4. スケジューリングアルゴリズム

### 4.1 基本的な流れ

```python
def schedule_patients():
    # 1. 患者を必要時間順にソート（180分患者を優先）
    sorted_patients = sort_by_requirements(patients)
    
    # 2. 各患者に対して最適な療法士・時間枠を割り当て
    for patient in sorted_patients:
        assignment = find_optimal_assignment(patient)
        if assignment:
            update_availability_matrices(assignment)
        else:
            add_to_unscheduled(patient)
    
    return schedule
```

### 4.2 最適化手法：線形割り当て問題

各患者の割り当てに `scipy.optimize.linear_sum_assignment` を使用：

```python
# コスト行列を作成（相性スコアの逆数×可用性）
cost_matrix = -compatibility_scores * availability_matrix

# 最適な割り当てを計算
therapist_indices, timeslot_indices = linear_sum_assignment(cost_matrix)
```

**なぜこの手法？**
- ハンガリアン法という効率的なアルゴリズムを使用
- 計算量：O(n³) で高速
- 最適解が保証される

### 4.3 制約の処理

#### Hard制約（絶対に守る必要がある）
- 患者の利用不可時間
- 療法士の勤務時間
- 必要最小療法時間

#### Soft制約（できるだけ守りたい）
- 担当療法士の優先
- 同性別・同病棟の優先

## 5. エラー処理とデバッグ

### 5.1 実行不可能な場合の検出

```python
class InfeasibleScheduleError(Exception):
    def __init__(self, patient_id, reason):
        self.patient_id = patient_id
        self.reason = reason
        super().__init__(f"患者{patient_id}をスケジュールできません: {reason}")
```

### 5.2 AIエージェントによる診断

スケジューリングが失敗した場合、AIエージェントが原因を分析：

```python
def diagnose_failure(error):
    # 制約行列を分析
    bottlenecks = find_bottlenecks()
    suggestions = generate_suggestions()
    
    return {
        "原因": "患者P123は利用可能時間枠が2つしかないが、9枠必要",
        "提案": "患者P123を14:00-15:00に利用可能にすることを検討"
    }
```

## 6. 実装のポイント

### 6.1 データの前処理

```python
# CP932エンコーディングでCSVを読み込み
df = pd.read_csv('therapist.csv', encoding='cp932')

# 病棟名の正規化
ward_mapping = {'西': 'W', '東': 'E'}
df['病棟'] = df['病棟'].map(ward_mapping)
```

### 6.2 時間枠の管理

```python
def generate_timeslots():
    """18個の20分枠を生成"""
    morning = ["09:00-09:20", "09:20-09:40", ...]  # 4枠
    afternoon = ["13:00-13:20", "13:20-13:40", ...]  # 14枠
    return morning + afternoon
```

### 6.3 メモリ効率の考慮

```python
# NumPy配列を使用してメモリ効率を向上
patient_availability = np.zeros((num_patients, 18), dtype=np.int8)
therapist_availability = np.zeros((num_therapists, 18), dtype=np.int8)
```

## 7. 会話型最適化

### 7.1 制約の動的変更

ユーザーが制約を変更したい場合：

```python
# ユーザー: "患者123を14:00に利用可能にして"
def update_patient_availability(patient_id, timeslot, available):
    patient_idx = patient_ids.index(patient_id)
    timeslot_idx = timeslot_to_index(timeslot)
    patient_availability[patient_idx, timeslot_idx] = 1 if available else 0
```

### 7.2 再スケジューリング

```python
def reschedule():
    # 変更された制約行列で再計算
    new_schedule = scheduler.schedule(updated_matrices)
    return new_schedule
```

## 8. 可視化とレポート

### 8.1 Ganttチャート生成

```python
def generate_gantt_chart(schedule):
    # Mermaidフォーマットでガントチャートを生成
    mermaid_code = f"""
    gantt
        title 理学療法スケジュール
        dateFormat HH:mm
        axisFormat %H:%M
        
        section 療法士1
        患者A : 09:00, 10:00
        患者B : 10:00, 11:00
    """
    return mermaid_code
```

### 8.2 Excel出力

```python
def export_to_excel(schedule, output_path):
    # 療法士別、時間別のスケジュール表を作成
    df = create_schedule_dataframe(schedule)
    df.to_excel(output_path, index=False)
```

## 9. パフォーマンス最適化

### 9.1 計算量の削減

- 制約行列の事前計算
- NumPyの並列処理活用
- 不要な再計算の回避

### 9.2 メモリ使用量の最適化

- int8データ型の使用（0/1フラグ）
- スパース行列の検討（将来的に）

## 10. テストとデバッグ

### 10.1 単体テスト

```python
def test_constraint_matrix_building():
    # 制約行列が正しく構築されるかテスト
    matrices = build_constraint_matrices(test_data)
    assert matrices.patient_availability.shape == (5, 18)
    assert matrices.compatibility.max() == 100
```

### 10.2 統合テスト

```python
def test_full_scheduling():
    # 実際のデータでスケジューリングが動作するかテスト
    schedule = run_full_scheduling(sample_data)
    assert len(schedule.unscheduled_patients) == 0
```

## まとめ

このシステムは以下の技術を組み合わせています：

1. **数学的最適化**: 制約充足問題として定式化
2. **効率的なデータ構造**: NumPy行列による高速計算
3. **アルゴリズム**: ハンガリアン法による最適割り当て
4. **AI支援**: 失敗時の診断と会話型最適化
5. **実用的な機能**: 可視化、Excel出力、エラー処理

初級開発者の方は、まず制約行列の概念を理解し、小さなサンプルデータで動作を確認することから始めることをお勧めします。
