///////////////////preamble
#let source = json(bytes(sys.inputs.data))

#set text(size: 10.5pt, font: "Liberation Serif")
#set page(
  header: align(center, text(size: 14pt, [*#source.at("personal details").name*])),
)

#show link: underline

#let contacts(personal_details) = {
  align(
    text(
      [
        #personal_details.phone | #link(personal_details.email) | #link(personal_details.linkedin) | #link(personal_details.github) | #personal_details.address | #personal_details.citizenship
      ],
      size: 12pt,
    ),
    center,
  )
}

#let education(education) = {
  for (edu) in education {
    v(0.1cm)
    if "school" in edu [
      #let school = edu.school
      _ #school.institute _  #h(1fr) #school.status
      - #school.primary with a concentration in #school.secondary
    ] else [
      I have no Certs yet SMH
    ]
  }
}

#let work_history(work) = {
  for (job) in work [
    #v(0.1cm)
    - _#job.title, #job.employer _, #job.city  #h(1fr) #job.start to #job.end
      #{ for bullet in job.highlights [- #bullet] }

  ]
}

#let projects(proj) = {
  for (ject) in proj [
    - _ #ject.name _  #h(1fr) #ject.start to #ject.end,

      #{
        if "link" in ject [
          - Project Link: #link(ject.link)
        ]
      }
      #{ for bullet in ject.highlights [- #bullet] }
  ]
}


/////////////////////////////////////////////////////
#contacts(source.at("personal details"))
#v(0.3cm)
== Education & Certificates
#education(source.education)
== Work History
#work_history(source.work_history)
== Projects
#v(0.1cm)
#projects(source.projects)
