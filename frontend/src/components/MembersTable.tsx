import { labelMatchesSearch } from '../labelMatch'
import type { MemberOut } from '../types'

interface MembersTableProps {
  members: MemberOut[]
  searchLabels?: string[]
  activeMemberId?: string
  onSelectMember: (member: MemberOut) => void
}

export function MembersTable({
  members,
  searchLabels = [],
  activeMemberId,
  onSelectMember,
}: MembersTableProps) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>DODID</th>
            <th>Name</th>
            <th>AFSC</th>
            <th>AFSC label</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => (
            <tr
              key={m.id}
              className={`row-clickable${activeMemberId === m.id ? ' row-active' : ''}`}
              tabIndex={0}
              onClick={() => onSelectMember(m)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onSelectMember(m)
                }
              }}
            >
              <td>{m.dodid}</td>
              <td>
                <div className="name-cell">
                  <span>{m.display_name}</span>
                  {m.personnel_type && (
                    <span className={`type-pill type-${m.personnel_type}`}>
                      {m.personnel_type.toUpperCase()}
                    </span>
                  )}
                </div>
              </td>
              <td>
                <code>{m.normalized_afsc}</code>
              </td>
              <td className="label-cell">
                {m.afsc_labels?.length ? (
                  <div className="label-pills">
                    {m.afsc_labels.map((label) => {
                      const active =
                        searchLabels.length > 0 && labelMatchesSearch(label, searchLabels)
                      return (
                        <span
                          key={label}
                          className={active ? 'label-pill label-pill-active' : 'label-pill'}
                        >
                          {label}
                        </span>
                      )
                    })}
                  </div>
                ) : (
                  '—'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
