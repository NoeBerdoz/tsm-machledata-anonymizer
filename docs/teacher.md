# The teacher v1

Issue #46 fine-tunes GLiNER2-PII (`fastino/gliner2-privacy-filter-PII-multi`) on our training data to get the teacher v1. As published, it misses 1,408 of the 7,275 entities of T1 (80.65 % recall), mostly of types its model card has no label for (see [baselines.md](baselines.md)).

## The labels

GLiNER2 takes its labels as plain names, so the teacher can learn new ones. `src/pii_anonymizer/teacher_labels.py` gives every type of our training data one GLiNER2 label. Two rules:

- When the model card has a label with the same meaning, we keep it, so that the model starts from what it already knows.
- When it has none, we add a new label, named after the type. The new labels are in **bold** below.

### OpenPII-1M

The 19 types of its card, plus `TIME`, which open-pii-masking-500k also has.

| Type | Label | | Type | Label |
|---|---|---|---|---|
| `GIVENNAME` | `first_name` | | `CITY` | `city` |
| `SURNAME` | `last_name` | | `ZIPCODE` | `postal_code` |
| `TITLE` | **`title`** | | `EMAIL` | `email` |
| `AGE` | **`age`** | | `TELEPHONENUM` | `phone_number` |
| `SEX` | **`sex`** | | `IDCARDNUM` | `government_id` |
| `GENDER` | **`gender`** | | `SOCIALNUM` | `national_id_number` |
| `DATE` | **`date`** | | `PASSPORTNUM` | `passport_number` |
| `TIME` | **`time`** | | `DRIVERLICENSENUM` | `drivers_license_number` |
| `STREET` | `street_address` | | `TAXNUM` | `tax_number` |
| `BUILDINGNUM` | **`building_number`** | | `CREDITCARDNUMBER` | `card_number` |

### Gretel (`gretelai/synthetic_pii_finance_multilingual`)

The 29 types of its card.

| Type | Label | | Type | Label |
|---|---|---|---|---|
| `name` | `full_name` | | `iban` | `iban` |
| `first_name` | `first_name` | | `bban` | `bank_account` |
| `last_name` | `last_name` | | `bank_routing_number` | `routing_number` |
| `company` | **`company`** | | `swift_bic_code` | **`swift_bic_code`** |
| `date`, `date_of_birth`, `date_time` | **`date`** | | `credit_card_number` | `card_number` |
| `time` | **`time`** | | `credit_card_security_code` | `card_cvv` |
| `email` | `email` | | `account_pin` | **`pin`** |
| `phone_number` | `phone_number` | | `customer_id` | `account_id` |
| `street_address` | `street_address` | | `employee_id` | **`employee_id`** |
| `local_latlng` | **`coordinates`** | | `user_name` | `username` |
| `ssn` | `national_id_number` | | `password` | `password` |
| `passport_number` | `passport_number` | | `api_key` | `api_key` |
| `driver_license_number` | `drivers_license_number` | | `ipv4`, `ipv6` | `ip_address` |

### Swiss values

The values of `swiss_training.py` ([swiss-identifiers.md](swiss-identifiers.md)) keep the label of their kind: `AVS` is `national_id_number`, like `SOCIALNUM`, `PHONE` is `phone_number` and `IBAN` is `iban`. A Gretel `bban` that receives a Swiss IBAN becomes `iban`.

### Choices

- **One label for all dates.** OpenPII-1M labels every date `DATE`, birth dates included, while Gretel splits `date`, `date_of_birth` and `date_time`. With two labels, the same kind of birth date would be `date` in one dataset and `date_of_birth` in the other, so the model would learn two answers for one text. Our recall does not depend on the label (an entity counts when all its characters are masked), so one label loses nothing.
- **`building_number` apart from `street_address`.** OpenPII-1M labels the street and the house number as two entities. Giving them the same label would teach the model two touching spans of one type.
- **`IDCARDNUM` is `government_id` and `SOCIALNUM` is `national_id_number`**, as in the first cloud run ([cloud-training.md](cloud-training.md)).
- **`company` is kept.** It is the third type of Gretel by count, and GLiNER2-PII finds only 28 % of the company names of the Swiss set. A company name can identify a person, for example a one-person business.
- **The card labels without training data are dropped**, such as `address`, `person`, `country`, `card_expiry` or `access_token`. The teacher is asked for the 35 labels of `TARGETS` only, so we measure what we trained.

Of these 35 labels, 12 are new: `title`, `age`, `sex`, `gender`, `date`, `time`, `building_number`, `company`, `coordinates`, `swift_bic_code`, `pin` and `employee_id`.
